"""Portfolio optimization — framework-free (no UI/DB imports).

An **equal-weight baseline** (always available) plus the user-selected methods:

Allocation (weights for a fixed set):
- ``inverse_volatility`` — weight inversely proportional to volatility;
- ``risk_parity`` — equal risk contribution (ERC);
- ``min_variance`` — minimum variance, Ledoit-Wolf covariance shrinkage;
- ``hrp`` — Hierarchical Risk Parity (López de Prado 2016).

Selection (pick which tickers from a universe):
- ``select_low_volatility`` — keep the lowest long-window-volatility names;
- ``select_by_clustering`` — correlation-cluster the universe, pick a representative each.

All allocators are **long-only**, weights **sum to 1**, with an optional **max-weight
cap**. They use only the supplied price window (look-ahead-safe) and **no expected-return
forecasts** (the robust choice — see ``docs/OPTIMIZATION_RESEARCH.md``). Deterministic.

Educational use only — not financial advice.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import minimize
from scipy.spatial.distance import squareform
from sklearn.covariance import LedoitWolf


def _returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Clean daily simple returns: aligned to the common window, no NaN, no flat assets.

    Drops all-NaN tickers, forward-fills internal gaps (look-ahead-safe), trims leading
    rows so the matrix starts where every remaining ticker has data, and drops
    zero-variance (flat/bad-data) columns — which otherwise break covariance/correlation
    and 1/vol math. So covariance, correlation, and Ledoit-Wolf never see NaN/inf.
    """
    clean = prices.sort_index().dropna(axis=1, how="all").ffill()
    returns = clean.pct_change().dropna(how="any")
    if returns.empty:
        return returns
    nonzero = returns.columns[returns.std() > 0]
    return returns[nonzero]


def _apply_cap(weights: pd.Series, cap: float) -> pd.Series:
    """Cap each weight at ``cap`` and redistribute the excess (waterfall), renormalize."""
    w = weights.clip(lower=0).astype(float)
    cap = max(cap, 1.0 / len(w))  # below 1/n is infeasible; clamp
    for _ in range(100):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        under = ~over
        room = w[under].sum()
        if room <= 0:
            break
        w[under] = w[under] + excess * w[under] / room
    return w / w.sum()


def _finalize(weights: pd.Series, max_weight: float | None) -> dict[str, float]:
    """Long-only, optional cap, renormalize to sum to 1; keys upper-cased."""
    w = weights.clip(lower=0).astype(float)
    if w.sum() <= 0:
        w = pd.Series(1.0, index=weights.index)
    w = w / w.sum()
    if max_weight is not None:
        w = _apply_cap(w, max_weight)
    return {str(k).upper(): float(v) for k, v in w.items()}


# --- baseline -------------------------------------------------------------------

def equal_weight(tickers: Sequence[str]) -> dict[str, float]:
    """1/N over the tickers — the always-present baseline."""
    syms = [str(t).upper() for t in tickers]
    if not syms:
        return {}
    return {t: 1.0 / len(syms) for t in syms}


# --- allocation methods (signature: prices, *, max_weight=None) ------------------

def inverse_volatility(
    prices: pd.DataFrame, *, max_weight: float | None = None
) -> dict[str, float]:
    vol = _returns(prices).std()
    vol = vol[vol > 0]
    if vol.empty:
        return equal_weight(list(prices.columns))
    return _finalize(1.0 / vol, max_weight)


def risk_parity(prices: pd.DataFrame, *, max_weight: float | None = None) -> dict[str, float]:
    """Equal risk contribution: each asset adds the same amount of portfolio risk."""
    returns = _returns(prices)
    cols = list(returns.columns)
    n = len(cols)
    if n == 0:
        return equal_weight(list(prices.columns))
    if n == 1:
        return {str(cols[0]).upper(): 1.0}
    cov = returns.cov().values
    inv_vol = 1.0 / np.sqrt(np.diag(cov))
    w0 = inv_vol / inv_vol.sum()  # inverse-vol start (≈ ERC for independent assets)

    def objective(w: np.ndarray) -> float:
        port_var = w @ cov @ w
        if port_var <= 0:
            return 0.0
        # percentage risk contributions (sum to 1) -> scale-free objective
        pct_rc = (w * (cov @ w)) / port_var
        return float(np.sum((pct_rc - 1.0 / n) ** 2))

    upper = max_weight if max_weight else 1.0
    result = minimize(
        objective,
        w0,
        method="SLSQP",
        bounds=[(1e-6, upper)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    # Fall back to the inverse-vol start if the solver didn't converge.
    weights = result.x if result.success else w0
    return _finalize(pd.Series(weights, index=cols), max_weight)


def min_variance(
    prices: pd.DataFrame, *, max_weight: float | None = None, shrinkage: bool = True
) -> dict[str, float]:
    """Minimum-variance long-only portfolio; Ledoit-Wolf covariance shrinkage by default."""
    returns = _returns(prices)
    cols = list(returns.columns)
    n = len(cols)
    if n == 0:
        return equal_weight(list(prices.columns))
    if n == 1:
        return {str(cols[0]).upper(): 1.0}
    cov = LedoitWolf().fit(returns.values).covariance_ if shrinkage else returns.cov().values

    upper = max_weight if max_weight else 1.0
    equal = np.full(n, 1.0 / n)
    result = minimize(
        lambda w: float(w @ cov @ w),
        equal,
        jac=lambda w: 2.0 * cov @ w,
        method="SLSQP",
        bounds=[(0.0, upper)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    # Fall back to equal weight if the solver didn't converge.
    weights = result.x if result.success else equal
    return _finalize(pd.Series(weights, index=cols), max_weight)


def hrp(prices: pd.DataFrame, *, max_weight: float | None = None) -> dict[str, float]:
    """Hierarchical Risk Parity: cluster by correlation, split risk down the tree."""
    returns = _returns(prices)
    cols = list(returns.columns)
    if len(cols) == 0:
        return equal_weight(list(prices.columns))
    if len(cols) == 1:
        return {str(cols[0]).upper(): 1.0}
    cov = returns.cov()
    corr = returns.corr()
    distance = np.sqrt(np.clip((1.0 - corr) / 2.0, 0.0, None))
    link = linkage(squareform(distance.values, checks=False), method="single")
    ordered = [cols[i] for i in _quasi_diag(link, len(cols))]
    return _finalize(_recursive_bisection(cov, ordered), max_weight)


def _quasi_diag(link: np.ndarray, num_items: int) -> list[int]:
    """Order leaves so similar assets sit together (HRP quasi-diagonalization)."""
    link = link.astype(int)
    sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
    while sort_ix.max() >= num_items:
        sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
        clusters = sort_ix[sort_ix >= num_items]
        i = clusters.index
        j = clusters.values - num_items
        sort_ix[i] = link[j, 0]
        sort_ix = pd.concat([sort_ix, pd.Series(link[j, 1], index=i + 1)]).sort_index()
        sort_ix.index = range(sort_ix.shape[0])
    return sort_ix.tolist()


def _inverse_variance_weights(cov_slice: pd.DataFrame) -> np.ndarray:
    ivp = 1.0 / np.diag(cov_slice.values)
    return ivp / ivp.sum()


def _cluster_variance(cov: pd.DataFrame, items: list[str]) -> float:
    sub = cov.loc[items, items]
    w = _inverse_variance_weights(sub)  # 1-D so the quadratic form is a scalar
    return float(w @ sub.values @ w)


def _recursive_bisection(cov: pd.DataFrame, ordered: list[str]) -> pd.Series:
    weights = pd.Series(1.0, index=ordered)
    clusters = [ordered]
    while clusters:
        nxt: list[list[str]] = []
        for cluster in clusters:
            if len(cluster) <= 1:
                continue
            half = len(cluster) // 2
            left, right = cluster[:half], cluster[half:]
            var_left = _cluster_variance(cov, left)
            var_right = _cluster_variance(cov, right)
            alpha = 1.0 - var_left / (var_left + var_right)
            weights[left] *= alpha
            weights[right] *= 1.0 - alpha
            nxt += [left, right]
        clusters = nxt
    return weights


# --- selection methods ----------------------------------------------------------

def select_low_volatility(prices: pd.DataFrame, k: int) -> list[str]:
    """Keep the ``k`` lowest-volatility tickers (long-window vol = low churn)."""
    vol = _returns(prices).std().sort_values()
    return [str(c).upper() for c in vol.index[:k]]


def select_by_clustering(prices: pd.DataFrame, k: int) -> list[str]:
    """Correlation-cluster the universe into ``k`` groups; pick the lowest-vol member each."""
    returns = _returns(prices)
    cols = list(returns.columns)
    if k >= len(cols):
        return [str(c).upper() for c in cols]
    corr = returns.corr()
    distance = np.sqrt(np.clip((1.0 - corr) / 2.0, 0.0, None))
    link = linkage(squareform(distance.values, checks=False), method="average")
    labels = fcluster(link, t=k, criterion="maxclust")
    vol = returns.std()
    chosen: list[str] = []
    for cluster_id in pd.unique(labels):
        members = [cols[i] for i in range(len(cols)) if labels[i] == cluster_id]
        chosen.append(str(min(members, key=lambda m: vol[m])).upper())
    return chosen


# --- dispatch -------------------------------------------------------------------

ALLOCATION_METHODS = {
    "Equal weight": lambda prices, *, max_weight=None: equal_weight(list(prices.columns)),
    "Risk parity": risk_parity,
    "Inverse-volatility": inverse_volatility,
    "Minimum-variance": min_variance,
    "Hierarchical Risk Parity": hrp,
}

SELECTION_METHODS = {
    "Low volatility": select_low_volatility,
    "Correlation clustering": select_by_clustering,
}


def allocate(
    method: str, prices: pd.DataFrame, *, max_weight: float | None = None
) -> dict[str, float]:
    return ALLOCATION_METHODS[method](prices, max_weight=max_weight)


def select(method: str, prices: pd.DataFrame, k: int) -> list[str]:
    return SELECTION_METHODS[method](prices, k)
