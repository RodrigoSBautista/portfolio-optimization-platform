"""Performance metrics — pure functions over a value/return-index series.

Framework-free (pandas/numpy only). Metrics are computed on a **time-weighted
return index** (growth of $1), so portfolios with cash contributions are measured
on investment performance alone, comparable apples-to-apples with a benchmark.

Metric definitions follow the project's ``finance-conventions`` skill:
- Sharpe / Sortino use an excess-return numerator over an annual risk-free rate
  (project default 4%/yr); Sortino's denominator is the downside deviation.
- Calmar = annualized return / |max drawdown|.
- Beta / annualized alpha come from an OLS of daily excess returns on a benchmark's
  daily excess returns.
- ``deflate`` converts a nominal value series to real ("today's dollars").
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252

# Project default annual risk-free rate (see finance-conventions skill). rf=0 is
# not an acceptable silent default in new code.
DEFAULT_RISK_FREE_RATE = 0.04

# Project default annual inflation rate for real ("today's dollars") deflation.
DEFAULT_INFLATION_PCT = 2.5


def daily_returns(index: pd.Series) -> pd.Series:
    """Simple daily returns of a value/return-index series (NaNs dropped)."""
    return index.pct_change().dropna()


def total_return(index: pd.Series) -> float:
    if len(index) < 2 or index.iloc[0] <= 0:
        return float("nan")
    return float(index.iloc[-1] / index.iloc[0] - 1.0)


def cagr(index: pd.Series) -> float:
    """Compound annual growth rate, using calendar time between first/last dates."""
    if len(index) < 2 or index.iloc[0] <= 0:
        return float("nan")
    days = (index.index[-1] - index.index[0]).days
    if days <= 0:
        return float("nan")
    years = days / 365.25
    return float((index.iloc[-1] / index.iloc[0]) ** (1.0 / years) - 1.0)


def annualized_volatility(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    if len(returns) < 2:
        return float("nan")
    return float(returns.std(ddof=1) * np.sqrt(periods_per_year))


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    """Annualized excess-return Sharpe ratio. ``risk_free_rate`` is an annual rate."""
    if len(returns) < 2:
        return float("nan")
    std = returns.std(ddof=1)
    if std == 0:
        return float("nan")
    excess = returns - risk_free_rate / periods_per_year
    return float(excess.mean() / std * np.sqrt(periods_per_year))


def sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    """Annualized Sortino ratio.

    Like Sharpe, but the denominator is the **downside deviation**: the standard
    deviation of the *negative* daily returns only, annualized by ``sqrt(periods)``.
    Returns NaN when there is no downside dispersion (no negatives / all-flat).
    """
    if len(returns) < 2:
        return float("nan")
    per_period_rf = risk_free_rate / periods_per_year
    excess = returns - per_period_rf
    downside = returns[returns < 0]
    if len(downside) == 0:
        return float("nan")
    # Population-style downside deviation about zero (ddof=0): RMS of negatives.
    downside_dev = float(np.sqrt(np.mean(np.square(downside))))
    if downside_dev == 0:
        return float("nan")
    return float(excess.mean() / downside_dev * np.sqrt(periods_per_year))


def max_drawdown(index: pd.Series) -> float:
    """Worst peak-to-trough decline (a negative number, e.g. -0.35 = -35%)."""
    if len(index) < 2:
        return float("nan")
    running_max = index.cummax()
    drawdown = index / running_max - 1.0
    return float(drawdown.min())


def calmar_ratio(index: pd.Series) -> float:
    """Calmar ratio = annualized return (CAGR) / |max drawdown|.

    Returns NaN when the drawdown is zero (division would be undefined/infinite).
    """
    mdd = max_drawdown(index)
    if not np.isfinite(mdd) or mdd == 0:
        return float("nan")
    ann_return = cagr(index)
    if not np.isfinite(ann_return):
        return float("nan")
    return float(ann_return / abs(mdd))


def calendar_year_returns(index: pd.Series) -> pd.Series:
    """Return the calendar-year total returns of a return-index series.

    Each year's return is ``last_value_of_year / last_value_of_prior_year - 1``. The
    first year uses the series' opening value as its base, so a series that starts
    mid-year still yields a (partial-year) figure for that first calendar year.
    """
    if len(index) < 2:
        return pd.Series(dtype=float)
    clean = index.dropna()
    if len(clean) < 2:
        return pd.Series(dtype=float)
    year_end = clean.groupby(clean.index.year).last()
    # Base each year on the prior year's close; the first year bases on the opening
    # value of the whole series (so a partial first year is still measured).
    bases = year_end.shift(1)
    bases.iloc[0] = clean.iloc[0]
    return (year_end / bases - 1.0).astype(float)


def best_year(index: pd.Series) -> float:
    """Best calendar-year return of the series (NaN if none computable)."""
    yr = calendar_year_returns(index)
    return float(yr.max()) if len(yr) else float("nan")


def worst_year(index: pd.Series) -> float:
    """Worst calendar-year return of the series (NaN if none computable)."""
    yr = calendar_year_returns(index)
    return float(yr.min()) if len(yr) else float("nan")


def return_index(prices: pd.Series) -> pd.Series:
    """Growth-of-$1 index from a price series (e.g. a benchmark's adjusted close)."""
    clean = prices.dropna()
    if clean.empty:
        return clean
    return clean / clean.iloc[0]


def deflate(series: pd.Series, annual_inflation_pct: float = DEFAULT_INFLATION_PCT) -> pd.Series:
    """Convert a nominal value series to real ("today's dollars").

    Divides each point by ``(1 + i) ** years_since_start`` where ``i`` is the annual
    inflation rate (as a percent, e.g. 2.5 -> 2.5%/yr) and years are calendar years
    (days / 365.25) elapsed since the series' first date. The first point is
    unchanged; label the result as "in today's dollars" (i.e. the start-date's
    purchasing power).
    """
    if series.empty:
        return series.astype(float)
    i = annual_inflation_pct / 100.0
    start = series.index[0]
    years = np.array([(ts - start).days / 365.25 for ts in series.index], dtype=float)
    factors = (1.0 + i) ** years
    return pd.Series(series.to_numpy(dtype=float) / factors, index=series.index)


def benchmark_stats(
    index: pd.Series,
    benchmark_index: pd.Series,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    periods_per_year: int = TRADING_DAYS,
) -> dict[str, float]:
    """Beta and annualized alpha of a return-index vs a benchmark return-index.

    OLS of the portfolio's **daily excess returns** on the benchmark's daily excess
    returns over their common dates::

        excess_p = alpha_daily + beta * excess_b + eps

    ``beta`` is the slope; ``alpha`` is the annualized intercept
    (``alpha_daily * periods_per_year``). Returns NaNs when there is insufficient
    overlap or the benchmark has zero variance.
    """
    rp = daily_returns(index)
    rb = daily_returns(benchmark_index)
    joined = pd.concat([rp, rb], axis=1, join="inner").dropna()
    if len(joined) < 2:
        return {"beta": float("nan"), "alpha": float("nan")}
    per_period_rf = risk_free_rate / periods_per_year
    x = joined.iloc[:, 1].to_numpy(dtype=float) - per_period_rf
    y = joined.iloc[:, 0].to_numpy(dtype=float) - per_period_rf
    var_x = np.var(x, ddof=1)
    if var_x == 0:
        return {"beta": float("nan"), "alpha": float("nan")}
    cov_xy = np.cov(x, y, ddof=1)[0, 1]
    beta = float(cov_xy / var_x)
    alpha_daily = float(y.mean() - beta * x.mean())
    alpha_annual = alpha_daily * periods_per_year
    return {"beta": beta, "alpha": alpha_annual}


def summarize(
    index: pd.Series,
    *,
    periods_per_year: int = TRADING_DAYS,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    benchmark_index: pd.Series | None = None,
) -> dict[str, float]:
    """Return the standard metric bundle for a return-index series.

    Existing keys are unchanged (``total_return``, ``cagr``, ``volatility``,
    ``sharpe``, ``max_drawdown``); new keys (``sortino``, ``calmar``, ``best_year``,
    ``worst_year``) are always added. When ``benchmark_index`` is supplied, ``beta``
    and ``alpha`` (annualized) are added too.
    """
    rets = daily_returns(index)
    out = {
        "total_return": total_return(index),
        "cagr": cagr(index),
        "volatility": annualized_volatility(rets, periods_per_year),
        "sharpe": sharpe_ratio(rets, risk_free_rate, periods_per_year),
        "max_drawdown": max_drawdown(index),
        "sortino": sortino_ratio(rets, risk_free_rate, periods_per_year),
        "calmar": calmar_ratio(index),
        "best_year": best_year(index),
        "worst_year": worst_year(index),
    }
    if benchmark_index is not None:
        out.update(benchmark_stats(index, benchmark_index, risk_free_rate, periods_per_year))
    return out
