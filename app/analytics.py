"""Framework-free analytics glue for the API (like ``app.sim_runner``).

Imports only ``core`` and ``data`` — no FastAPI/Streamlit. Two families of helpers:

- **Projection inputs** (``portfolio_daily_returns``, ``monthly_contribution_from_spec``):
  derive the daily-return series and monthly cash flow a ``PortfolioSpec`` implies, so
  the ``/project`` and ``/retirement`` endpoints can feed ``core.projection`` without
  re-implementing simulation or the benchmark-as-holding dedupe.
- **Multi-asset analytics** (``efficient_frontier``, ``diversification``): sample random
  long-only portfolios for the risk/return cloud + Pareto frontier, and build the
  correlation matrix / hierarchical clusters / risk contributions for a ticker set.

All look-ahead-safe: they consume the common-window-aligned adjusted prices ``data/``
returns and never fabricate data across gaps.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from app.sim_runner import SimError, run_simulation
from core.portfolio import RECURRING, PortfolioSpec
from data.provider import common_history

TRADING_DAYS = 252
MONTHS_PER_YEAR = 12

# Recurring cadence -> contributions per month (to normalize a spec's DCA flow to a
# single monthly figure for the projection engine). Mirrors ``core.simulation``'s
# supported cadences; unknown names fall back to "treat as monthly".
_PER_MONTH: dict[str, float] = {
    "daily": TRADING_DAYS / MONTHS_PER_YEAR,
    "weekly": 52.0 / MONTHS_PER_YEAR,
    "monthly": 1.0,
    "every 2 months": 1.0 / 2.0,
    "quarterly": 1.0 / 3.0,
    "every 6 months": 1.0 / 6.0,
    "annually": 1.0 / MONTHS_PER_YEAR,
    "yearly": 1.0 / MONTHS_PER_YEAR,
}


class AnalyticsError(ValueError):
    """Raised when an analytic can't run (no data / no overlap / degenerate input)."""


# --------------------------------------------------------------------------- #
# Projection inputs (shared by /project and /retirement)
# --------------------------------------------------------------------------- #
def portfolio_daily_returns(spec: PortfolioSpec, prices: pd.DataFrame) -> pd.Series:
    """Daily simple returns of ``spec``'s time-weighted growth over ``prices``.

    Runs the canonical ``run_simulation`` (which aligns to a common window and dedupes a
    benchmark that is also a holding), then differences the resulting ``twr_index`` — so
    contributions never leak into the returns fed to the Monte Carlo engines.
    """
    try:
        result = run_simulation(spec, prices)
    except SimError as exc:
        raise AnalyticsError(str(exc)) from exc
    returns = result.sim["twr_index"].pct_change().dropna()
    if returns.empty:
        raise AnalyticsError("Not enough price history to derive daily returns.")
    return returns


def monthly_contribution_from_spec(spec: PortfolioSpec) -> tuple[float, float]:
    """(monthly_contribution, escalation_pct) implied by ``spec``'s contributions.

    Reuses ``spec.simulation_kwargs`` (recurring amount + frequency) and normalizes the
    recurring cash flow to a per-**month** dollar figure the projection engine expects
    (e.g. weekly -> amount*52/12, quarterly -> amount/3). Spec contributions carry no
    escalation, so ``escalation_pct`` is always ``0.0`` here (documented, not guessed).
    """
    recurring = next((c for c in spec.contributions if c.kind == RECURRING), None)
    if recurring is None or not recurring.amount:
        return 0.0, 0.0
    freq = (recurring.frequency or "monthly").lower()
    per_month = _PER_MONTH.get(freq, 1.0)
    return float(recurring.amount) * per_month, 0.0


# --------------------------------------------------------------------------- #
# Multi-asset analytics (efficient frontier + diversification)
# --------------------------------------------------------------------------- #
def _aligned_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Common-window daily returns with all-NaN and zero-variance columns dropped.

    So covariance/correlation never see NaN/inf and a flat (bad-data) series can't
    poison the matrix. Raises ``AnalyticsError`` when nothing usable survives.
    """
    aligned = common_history(prices)
    if aligned.empty:
        raise AnalyticsError("No overlapping price history for these tickers.")
    returns = aligned.pct_change().dropna(how="any")
    if returns.empty:
        raise AnalyticsError("Not enough overlapping history to compute returns.")
    nonzero = returns.columns[returns.std(ddof=1) > 0]
    returns = returns[nonzero]
    if returns.shape[1] < 2:
        raise AnalyticsError("Need at least two tickers with variance in the window.")
    return returns


def _ret_vol(daily_matrix: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    """Annualized (return, vol) of a single weight vector over a daily-return matrix."""
    port = daily_matrix @ weights
    ann_ret = float(port.mean() * TRADING_DAYS)
    ann_vol = float(port.std(ddof=1) * np.sqrt(TRADING_DAYS))
    return ann_ret, ann_vol


def efficient_frontier(
    prices: pd.DataFrame,
    *,
    n_samples: int = 2000,
    seed: int = 42,
    extra_points: list[dict] | None = None,
) -> dict:
    """Random-portfolio risk/return cloud, Pareto frontier, and comparison markers.

    Samples ``n_samples`` long-only Dirichlet weight vectors (seeded), computes each
    portfolio's annualized return (mean daily x 252) and vol (std x sqrt(252)); the
    frontier is the Pareto upper-left set (sorted by vol, keep running-max return).
    Markers = equal-weight plus each ``extra_points`` entry (its weights renormalized
    over the tickers present after alignment; missing tickers ignored).
    """
    returns = _aligned_returns(prices)
    tickers = list(returns.columns)
    k = len(tickers)
    R = returns.to_numpy(dtype=float)  # (T, k)

    rng = np.random.default_rng(seed)
    W = rng.dirichlet(np.ones(k), size=n_samples)  # (n_samples, k), long-only sum-1
    port = R @ W.T  # (T, n_samples)
    ann_ret = port.mean(axis=0) * TRADING_DAYS
    ann_vol = port.std(axis=0, ddof=1) * np.sqrt(TRADING_DAYS)

    cloud = [
        {"vol": round(float(v), 6), "ret": round(float(r), 6)}
        for v, r in zip(ann_vol, ann_ret, strict=True)
    ]

    # Pareto upper-left: sort by vol asc (ties: ret desc), keep strictly-improving ret.
    order = np.lexsort((-ann_ret, ann_vol))
    frontier: list[dict] = []
    best = -np.inf
    for i in order:
        if ann_ret[i] > best + 1e-12:
            best = ann_ret[i]
            frontier.append(
                {"vol": round(float(ann_vol[i]), 6), "ret": round(float(ann_ret[i]), 6)}
            )

    markers: list[dict] = []
    eq = np.full(k, 1.0 / k)
    eq_ret, eq_vol = _ret_vol(R, eq)
    markers.append({"label": "Equal weight", "vol": round(eq_vol, 6), "ret": round(eq_ret, 6)})
    for point in extra_points or []:
        label = str(point.get("label", "Portfolio"))
        raw = {str(t).upper(): float(w) for t, w in (point.get("weights") or {}).items()}
        w = np.array([raw.get(t, 0.0) for t in tickers], dtype=float)
        total = w.sum()
        if total <= 0:
            continue  # no overlap with the aligned tickers -> skip this marker
        w = w / total
        ret, vol = _ret_vol(R, w)
        markers.append({"label": label, "vol": round(vol, 6), "ret": round(ret, 6)})

    return {"cloud": cloud, "frontier": frontier, "markers": markers}


def diversification(
    prices: pd.DataFrame, *, weights: dict[str, float] | None = None
) -> dict:
    """Correlation matrix, hierarchical clusters, and risk contributions for a set.

    - matrix: symmetric daily-return correlation (1.0 diagonal), rounded to 4dp.
    - clusters: hierarchical (average linkage on sqrt((1-corr)/2) distance), cut to
      ``min(4, n)`` groups (same approach as ``core.optimization``).
    - risk_contributions: **fractional** contribution to portfolio variance,
      ``pct_i = w_i (Sigma w)_i / (w' Sigma w)``, summing to ~1.0 (weights renormalized
      over available tickers; equal-weight by default), sorted descending. The React
      charts multiply by 100 for display.
    """
    returns = _aligned_returns(prices)
    tickers = list(returns.columns)
    n = len(tickers)

    corr = returns.corr()
    values = [[round(float(corr.iat[i, j]), 4) for j in range(n)] for i in range(n)]
    for i in range(n):
        values[i][i] = 1.0
    matrix = {"tickers": tickers, "values": values}

    # Hierarchical clusters on correlation distance.
    distance = np.sqrt(np.clip((1.0 - corr.to_numpy()) / 2.0, 0.0, None))
    link = linkage(squareform(distance, checks=False), method="average")
    k = min(4, n)
    labels = fcluster(link, t=k, criterion="maxclust")
    clusters: list[dict] = []
    for c_num, cluster_id in enumerate(pd.unique(labels), start=1):
        members = [tickers[i] for i in range(n) if labels[i] == cluster_id]
        clusters.append({"label": f"Cluster {c_num}", "members": members})

    # Risk contributions (scale-free -> daily covariance is fine).
    raw = {str(t).upper(): float(w) for t, w in (weights or {}).items()}
    w = np.array([raw.get(t, 0.0) for t in tickers], dtype=float)
    if w.sum() <= 0:
        w = np.full(n, 1.0 / n)  # default equal weight
    else:
        w = w / w.sum()
    cov = returns.cov().to_numpy(dtype=float)
    sigma_w = cov @ w
    port_var = float(w @ sigma_w)
    if port_var <= 0:
        pct = np.full(n, 1.0 / n)
    else:
        pct = w * sigma_w / port_var  # fractions summing to ~1.0
    contribs = [
        {"ticker": tickers[i], "pct": round(float(pct[i]), 6)} for i in range(n)
    ]
    contribs.sort(key=lambda d: d["pct"], reverse=True)

    return {"matrix": matrix, "clusters": clusters, "risk_contributions": contribs}
