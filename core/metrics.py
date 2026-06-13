"""Performance metrics — pure functions over a value/return-index series.

Framework-free (pandas/numpy only). Metrics are computed on a **time-weighted
return index** (growth of $1), so portfolios with cash contributions are measured
on investment performance alone, comparable apples-to-apples with a benchmark.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


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
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    """Annualized Sharpe ratio. ``risk_free_rate`` is an annual rate."""
    if len(returns) < 2:
        return float("nan")
    std = returns.std(ddof=1)
    if std == 0:
        return float("nan")
    excess = returns - risk_free_rate / periods_per_year
    return float(excess.mean() / std * np.sqrt(periods_per_year))


def max_drawdown(index: pd.Series) -> float:
    """Worst peak-to-trough decline (a negative number, e.g. -0.35 = -35%)."""
    if len(index) < 2:
        return float("nan")
    running_max = index.cummax()
    drawdown = index / running_max - 1.0
    return float(drawdown.min())


def return_index(prices: pd.Series) -> pd.Series:
    """Growth-of-$1 index from a price series (e.g. a benchmark's adjusted close)."""
    clean = prices.dropna()
    if clean.empty:
        return clean
    return clean / clean.iloc[0]


def summarize(index: pd.Series, *, periods_per_year: int = TRADING_DAYS) -> dict[str, float]:
    """Return the standard metric bundle for a return-index series."""
    rets = daily_returns(index)
    return {
        "total_return": total_return(index),
        "cagr": cagr(index),
        "volatility": annualized_volatility(rets, periods_per_year),
        "sharpe": sharpe_ratio(rets, periods_per_year=periods_per_year),
        "max_drawdown": max_drawdown(index),
    }
