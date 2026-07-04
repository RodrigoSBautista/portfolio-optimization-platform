"""Forward projections — block-bootstrap Monte Carlo & withdrawal (drawdown) analysis.

Framework-free (pandas/numpy only), fully **seeded** and deterministic. These are
*resamplings of history*, not forecasts: we sample moving blocks of the supplied
daily returns (preserving fat tails and short-run autocorrelation), never assume
i.i.d. normal, and always report **percentile bands / distributions** — never a
single predicted path.

Honesty rule (see the ``finance-conventions`` skill and ``PROJECTION_CAVEAT``):
always surface that projections resample the past, the future can differ, and this
is not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252
MONTHS_PER_YEAR = 12
PERCENTILES = (5, 25, 50, 75, 95)

PROJECTION_CAVEAT = (
    "Projections resample historical returns (block bootstrap); they are not "
    "forecasts. The future can differ materially from the past, and results are "
    "shown as probability bands, not a single predicted path. Not financial advice."
)


# --------------------------------------------------------------------------- #
# Block bootstrap
# --------------------------------------------------------------------------- #
def _bootstrap_daily_paths(
    returns: pd.Series,
    *,
    n_days: int,
    n_paths: int,
    block_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return an ``(n_paths, n_days)`` array of bootstrapped daily simple returns.

    Moving-block bootstrap: overlapping blocks of ``block_size`` consecutive daily
    returns are sampled with replacement and concatenated until each path reaches
    ``n_days`` (then truncated). Preserves short-run autocorrelation / fat tails.
    """
    r = returns.dropna().to_numpy(dtype=float)
    if r.size == 0:
        raise ValueError("returns series is empty after dropping NaNs")
    # Guard against bad-data rows: a return <= -100% would zero the cumulative path
    # and poison every percentile with NaN (0/0). Clip just above total loss.
    r = np.clip(r, -0.9999, None)
    block_size = max(1, min(block_size, r.size))
    n_blocks_available = r.size - block_size + 1  # overlapping moving blocks

    # Blocks needed per path (ceil), sampled as starting indices with replacement.
    blocks_per_path = int(np.ceil(n_days / block_size))
    starts = rng.integers(0, n_blocks_available, size=(n_paths, blocks_per_path))

    # Gather each block's rows via broadcasting: offsets 0..block_size-1.
    offsets = np.arange(block_size)
    # idx shape: (n_paths, blocks_per_path, block_size)
    idx = starts[:, :, None] + offsets[None, None, :]
    sampled = r[idx]  # same shape
    paths = sampled.reshape(n_paths, blocks_per_path * block_size)[:, :n_days]
    return paths


# --------------------------------------------------------------------------- #
# Monte Carlo accumulation projection
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ProjectionResult:
    """Result of :func:`project_monte_carlo`.

    Attributes:
        bands: DataFrame indexed by month (0..years*12) with columns
            ``p5, p25, p50, p75, p95`` — portfolio-value percentiles across paths.
        terminal_percentiles: dict pXX -> terminal-value percentile.
        contributed: Series indexed by month of cumulative cash contributed
            (deterministic; identical across paths).
        terminal_values: 1-D array of each path's terminal value (for custom stats).
        caveat: the honesty caveat string.
    """

    bands: pd.DataFrame
    terminal_percentiles: dict[str, float]
    contributed: pd.Series
    terminal_values: np.ndarray
    caveat: str = PROJECTION_CAVEAT

    def goal_probability(self, goal: float) -> float:
        """Share of paths whose terminal value is >= ``goal`` (in [0, 1])."""
        if self.terminal_values.size == 0:
            return float("nan")
        return float(np.mean(self.terminal_values >= goal))


def _monthly_step_boundaries(years: int) -> np.ndarray:
    """Daily-step index at the END of each of the ``years*12`` months (1-based days).

    Month ``m`` (1..N) ends at daily step ``round(m * 252 / 12)`` so months tile the
    ``252*years`` daily horizon evenly. Month 0 is the starting point (day 0).
    """
    n_months = years * MONTHS_PER_YEAR
    months = np.arange(1, n_months + 1)
    return np.rint(months * TRADING_DAYS / MONTHS_PER_YEAR).astype(int)


def project_monte_carlo(
    returns: pd.Series,
    *,
    years: int,
    n_paths: int = 1000,
    block_size: int = 21,
    seed: int = 42,
    start_value: float,
    monthly_contribution: float = 0.0,
    escalation_pct: float = 0.0,
) -> ProjectionResult:
    """Block-bootstrap Monte Carlo projection of portfolio value.

    Simulates ``n_paths`` value paths over ``252*years`` bootstrapped daily returns,
    seeded by ``seed`` (deterministic). A ``monthly_contribution`` is added at the end
    of each simulated month, optionally escalated by ``escalation_pct`` per year (the
    year-``k`` monthly contribution is ``monthly_contribution * (1+e)**k``). Output is
    downsampled to monthly percentile bands.

    Args:
        returns: historical daily simple returns of the portfolio.
        years: projection horizon in whole years (>= 1).
        n_paths: number of bootstrap paths.
        block_size: moving-block length in trading days (~21 = 1 month).
        seed: RNG seed for reproducibility.
        start_value: initial portfolio value at month 0.
        monthly_contribution: cash added at the end of each month.
        escalation_pct: annual growth of the monthly contribution (percent).

    Returns:
        ProjectionResult with monthly bands, terminal percentiles, contributed series.
    """
    if years < 1:
        raise ValueError("years must be >= 1")
    if n_paths < 1:
        raise ValueError("n_paths must be >= 1")
    if start_value < 0 or monthly_contribution < 0:
        raise ValueError("start_value and monthly_contribution must be non-negative")
    if escalation_pct < 0:
        raise ValueError("escalation_pct must be non-negative")

    rng = np.random.default_rng(seed)
    n_days = years * TRADING_DAYS
    daily = _bootstrap_daily_paths(
        returns, n_days=n_days, n_paths=n_paths, block_size=block_size, rng=rng
    )

    month_end_days = _monthly_step_boundaries(years)  # length years*12, values 1..n_days
    n_months = month_end_days.size
    escalation = escalation_pct / 100.0

    # Growth factor per day, and cumulative product to value each day cheaply.
    growth = 1.0 + daily  # (n_paths, n_days)
    cum = np.cumprod(growth, axis=1)  # value multiple of day-0 dollars at each day

    # Walk month by month applying contributions at each month end. We track each
    # path's value and the cumulative contributed cash (deterministic).
    values = np.full(n_paths, float(start_value))
    contributed_running = float(start_value)
    band_rows: list[np.ndarray] = []
    contributed_rows: list[float] = []

    # Month 0 (starting point, before any bootstrapped growth or contribution).
    band_rows.append(np.percentile(values, PERCENTILES))
    contributed_rows.append(contributed_running)

    prev_day = 0
    for m in range(n_months):
        end_day = month_end_days[m]
        # Multiplicative growth of existing holdings over this month's daily steps.
        # cum[:, end_day-1] / cum[:, prev_day-1] is the segment return (prev_day-1 = -1
        # meaning "1.0" for the first segment).
        seg_end = cum[:, end_day - 1]
        seg_start = cum[:, prev_day - 1] if prev_day > 0 else np.ones(n_paths)
        values = values * (seg_end / seg_start)
        # Contribution at month end, escalated by completed years.
        year_k = m // MONTHS_PER_YEAR
        contrib = monthly_contribution * (1.0 + escalation) ** year_k
        values = values + contrib
        contributed_running += contrib
        band_rows.append(np.percentile(values, PERCENTILES))
        contributed_rows.append(contributed_running)
        prev_day = end_day

    band_index = pd.RangeIndex(0, n_months + 1, name="month")
    bands = pd.DataFrame(
        np.vstack(band_rows),
        columns=[f"p{p}" for p in PERCENTILES],
        index=band_index,
    )
    contributed = pd.Series(contributed_rows, index=band_index, name="contributed")
    terminal_values = values.copy()
    terminal_percentiles = {
        f"p{p}": float(np.percentile(terminal_values, p)) for p in PERCENTILES
    }
    return ProjectionResult(
        bands=bands,
        terminal_percentiles=terminal_percentiles,
        contributed=contributed,
        terminal_values=terminal_values,
    )


# --------------------------------------------------------------------------- #
# Withdrawal (drawdown / retirement) analysis
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class WithdrawalResult:
    """Result of :func:`simulate_withdrawals`.

    Attributes:
        success_rate: share of paths that funded every scheduled withdrawal over the
            horizon (a path ending at exactly $0 after its final withdrawal counts
            as a success).
        bands: monthly balance percentile bands (``p5..p95``) indexed by month.
        years_lasted_percentiles: dict pXX -> years the balance lasted (paths that
            survive the full horizon are recorded as ``years``).
        years_lasted: 1-D array of years-lasted per path.
        caveat: the honesty caveat string.
    """

    success_rate: float
    bands: pd.DataFrame
    years_lasted_percentiles: dict[str, float]
    years_lasted: np.ndarray
    caveat: str = PROJECTION_CAVEAT


def simulate_withdrawals(
    returns: pd.Series,
    *,
    start_balance: float,
    years: int,
    withdrawal: float,
    withdrawal_is_rate: bool = False,
    inflation_pct: float = 2.5,
    n_paths: int = 1000,
    block_size: int = 21,
    seed: int = 42,
) -> WithdrawalResult:
    """Monte Carlo withdrawal (sustainable-spending) analysis.

    Each month a withdrawal is taken from the balance, then the balance grows by that
    month's bootstrapped return. ``withdrawal`` is either a fixed monthly dollar amount
    (default) or, when ``withdrawal_is_rate=True``, an **annual** withdrawal rate as a
    percent of the *starting* balance (e.g. 4.0 -> 4%/yr, taken as 1/12 monthly).
    Fixed-dollar withdrawals grow with ``inflation_pct`` each year; rate-based
    withdrawals are a fixed dollar amount off the starting balance (already inflation-
    neutral in real terms is not assumed — kept simple and documented).

    A path "fails" the first month its balance cannot cover the withdrawal (depleted).

    Returns:
        WithdrawalResult with success rate, monthly balance bands, years-lasted stats.
    """
    if years < 1:
        raise ValueError("years must be >= 1")
    if n_paths < 1:
        raise ValueError("n_paths must be >= 1")
    if start_balance < 0 or withdrawal < 0:
        raise ValueError("start_balance and withdrawal must be non-negative")
    if inflation_pct < 0:
        raise ValueError("inflation_pct must be non-negative")

    rng = np.random.default_rng(seed)
    n_days = years * TRADING_DAYS
    daily = _bootstrap_daily_paths(
        returns, n_days=n_days, n_paths=n_paths, block_size=block_size, rng=rng
    )
    cum = np.cumprod(1.0 + daily, axis=1)

    if withdrawal_is_rate:
        base_monthly = start_balance * (withdrawal / 100.0) / MONTHS_PER_YEAR
    else:
        base_monthly = withdrawal
    inflation = inflation_pct / 100.0

    month_end_days = _monthly_step_boundaries(years)
    n_months = month_end_days.size

    balances = np.full(n_paths, float(start_balance))
    depleted = np.zeros(n_paths, dtype=bool)
    months_lasted = np.full(n_paths, n_months, dtype=float)

    band_rows: list[np.ndarray] = [np.percentile(balances, PERCENTILES)]

    prev_day = 0
    for m in range(n_months):
        end_day = month_end_days[m]
        # Withdrawal at the start of the month (fixed-dollar grows with inflation).
        year_k = m // MONTHS_PER_YEAR
        if withdrawal_is_rate:
            wd = base_monthly
        else:
            wd = base_monthly * (1.0 + inflation) ** year_k

        # Take withdrawal; mark newly-depleted paths (can't fund it) at zero.
        newly_depleted = (~depleted) & (balances < wd)
        if newly_depleted.any():
            months_lasted[newly_depleted] = m  # lasted m completed months
            balances[newly_depleted] = 0.0
            depleted |= newly_depleted

        active = ~depleted
        balances[active] = balances[active] - wd

        # Grow surviving balances over the month.
        seg_end = cum[:, end_day - 1]
        seg_start = cum[:, prev_day - 1] if prev_day > 0 else np.ones(n_paths)
        month_growth = seg_end / seg_start
        balances[active] = balances[active] * month_growth[active]
        balances[depleted] = 0.0

        band_rows.append(np.percentile(balances, PERCENTILES))
        prev_day = end_day

    band_index = pd.RangeIndex(0, n_months + 1, name="month")
    bands = pd.DataFrame(
        np.vstack(band_rows),
        columns=[f"p{p}" for p in PERCENTILES],
        index=band_index,
    )

    success_rate = float(np.mean(~depleted))
    years_lasted = months_lasted / MONTHS_PER_YEAR
    years_lasted_percentiles = {
        f"p{p}": float(np.percentile(years_lasted, p)) for p in PERCENTILES
    }
    return WithdrawalResult(
        success_rate=success_rate,
        bands=bands,
        years_lasted_percentiles=years_lasted_percentiles,
        years_lasted=years_lasted,
    )
