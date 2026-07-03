"""Historical growth simulation — buy-and-hold with optional periodic rebalancing.

Pure pandas/numpy; framework-free. Supports a **lump sum** and **recurring (DCA)**
contributions. Strictly **look-ahead-safe**: every buy/rebalance uses that day's
price and the loop runs strictly forward in time.

The result carries three series so the UI can tell the full story:
- ``value``     — actual portfolio market value (includes contributions);
- ``invested``  — cumulative cash contributed (cost basis);
- ``twr_index`` — time-weighted growth of $1 (contributions removed), used for metrics.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
from pandas.tseries.frequencies import to_offset

# Trading days per year (annualization / daily fee-decay factor).
TRADING_DAYS = 252

# Friendly frequency names -> pandas date_range offset (period-start steps).
# Supports plain N-month cadences (e.g. every 2 / 6 months) that to_period can't.
_FREQ_OFFSETS = {
    "daily": "D",
    "weekly": "W",
    "monthly": "MS",
    "every 2 months": "2MS",
    "quarterly": "QS",
    "every 6 months": "6MS",
    "annually": "YS",
    "yearly": "YS",
}


def normalize_weights(
    weights: Mapping[str, float], available: list[str]
) -> dict[str, float]:
    """Validate weights against available tickers and rescale them to sum to 1."""
    available_upper = {str(c).upper() for c in available}
    cleaned: dict[str, float] = {}
    for ticker, weight in weights.items():
        if weight < 0:
            raise ValueError(f"weight for {ticker} is negative")
        key = ticker.upper()
        if key not in available_upper:
            raise ValueError(f"{ticker} has no price data")
        cleaned[key] = cleaned.get(key, 0.0) + float(weight)
    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError("weights must sum to a positive number")
    return {k: v / total for k, v in cleaned.items()}


def _align(prices: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Trim to the window where every ticker has data, then forward-fill gaps.

    Bounds the result to ``[max(first_valid), min(last_valid)]`` so non-overlapping
    histories yield an empty frame (rather than fabricating prices across a gap), and
    a delisted ticker's price is never carried past its last trading day. Forward-fill
    within the window uses only past data, so the result stays look-ahead-safe.
    """
    px = prices[tickers].sort_index()
    firsts = [px[c].first_valid_index() for c in px.columns]
    lasts = [px[c].last_valid_index() for c in px.columns]
    if any(f is None for f in firsts):
        return px.iloc[0:0]
    start, end = max(firsts), min(lasts)
    if start > end:
        return px.iloc[0:0]
    return px.loc[start:end].ffill()


def _contribution_dates(index: pd.DatetimeIndex, freq: str) -> set[pd.Timestamp]:
    """Trading days on which a periodic action (contribution/rebalance) fires.

    Builds period boundaries at the given cadence over the index span and snaps each
    boundary **forward** to the first trading day on/after it (look-ahead-safe). The
    range starts one step before the first day so the first period is included (the
    first action lands on day one). Supports N-month cadences (every 2 / 6 months).
    """
    offset = _FREQ_OFFSETS.get(freq.lower(), freq)
    start = index[0] - to_offset(offset)
    boundaries = pd.date_range(start=start, end=index[-1], freq=offset)
    positions = index.searchsorted(boundaries, side="left")
    return {index[i] for i in positions if i < len(index)}


def simulate_portfolio(
    prices: pd.DataFrame,
    weights: Mapping[str, float],
    *,
    lump_sum: float = 0.0,
    recurring_amount: float = 0.0,
    recurring_freq: str | None = None,
    rebalance: str | None = None,
    escalation_pct: float = 0.0,
    annual_fee_pct: float = 0.0,
) -> pd.DataFrame:
    """Simulate portfolio growth over the price history.

    Args:
        prices: [date x ticker] adjusted close prices.
        weights: target weights per ticker (rescaled to sum to 1).
        lump_sum: cash invested on the first day.
        recurring_amount: cash invested each ``recurring_freq`` period.
        recurring_freq: e.g. "monthly", "weekly", "quarterly", or a pandas alias.
        rebalance: rebalance cadence (same vocabulary as ``recurring_freq``), or None.
        escalation_pct: annual growth (as a percent, e.g. 5.0 -> 5%/yr) applied to the
            recurring contribution amount on each anniversary of the first contribution
            date. Year 1 contributes ``recurring_amount``; on/after the first
            anniversary it contributes ``recurring_amount * (1 + e)``; after the second,
            ``* (1 + e) ** 2``; etc. Look-ahead-safe (depends only on elapsed time).
        annual_fee_pct: explicit advisory-fee drag (as a percent, e.g. 1.0 -> 1%/yr)
            applied as a daily multiplicative decay ``(1 - fee) ** (1/252)`` to the
            portfolio value each trading day. NOTE: fund expense ratios are ALREADY
            embedded in the dividend-adjusted prices — do NOT use this for those; it is
            only for a user-supplied advisory fee on top of them.

    Returns:
        DataFrame indexed by date with columns ``value``, ``invested``, ``twr_index``.
    """
    if lump_sum < 0 or recurring_amount < 0:
        raise ValueError("contribution amounts must be non-negative")
    if escalation_pct < 0:
        raise ValueError("escalation_pct must be non-negative")
    if not 0.0 <= annual_fee_pct < 100.0:
        raise ValueError("annual_fee_pct must be in [0, 100)")

    weights = normalize_weights(weights, list(prices.columns))
    tickers = list(weights)
    px = _align(prices, tickers)
    if px.empty:
        raise ValueError("no overlapping price history for the selected tickers")

    dates = px.index
    w = pd.Series(weights)

    contrib_days: set[pd.Timestamp] = set()
    if recurring_amount > 0 and recurring_freq:
        contrib_days = _contribution_dates(dates, recurring_freq)

    rebal_days: set[pd.Timestamp] = set()
    if rebalance:
        rebal_days = _contribution_dates(dates, rebalance)
        rebal_days.discard(dates[0])  # nothing to rebalance on day one

    escalation = escalation_pct / 100.0
    # First contribution date anchors the escalation anniversaries; None until reached.
    first_contrib_date = min(contrib_days) if contrib_days else None
    # Daily advisory-fee decay factor (1.0 when no fee).
    fee_daily = (1.0 - annual_fee_pct / 100.0) ** (1.0 / TRADING_DAYS)

    shares = pd.Series(0.0, index=tickers)
    invested = 0.0
    prev_value = 0.0
    values: list[float] = []
    invested_hist: list[float] = []
    twr_factors: list[float] = []

    for i, day in enumerate(dates):
        price_today = px.loc[day]

        # 0) advisory-fee drag: decay existing holdings BEFORE measuring returns/cash.
        if fee_daily != 1.0 and (shares != 0.0).any():
            shares = shares * fee_daily

        # 1) value of existing holdings BEFORE today's cash flow -> time-weighted factor
        value_before = float((shares * price_today).sum())
        twr_factors.append(value_before / prev_value if prev_value > 0 else 1.0)

        # 2) contributions: lump sum on day one, recurring on period-start days
        cash = lump_sum if i == 0 else 0.0
        if day in contrib_days:
            years_elapsed = (day - first_contrib_date).days // 365
            cash += recurring_amount * (1.0 + escalation) ** years_elapsed
        if cash > 0:
            shares = shares + (cash * w) / price_today
            invested += cash

        # 3) rebalance back to target weights at today's price (no cash flow)
        if day in rebal_days:
            total = float((shares * price_today).sum())
            if total > 0:
                shares = (total * w) / price_today

        value_after = float((shares * price_today).sum())
        values.append(value_after)
        invested_hist.append(invested)
        prev_value = value_after

    twr_index = pd.Series(twr_factors, index=dates).cumprod()
    return pd.DataFrame(
        {"value": values, "invested": invested_hist, "twr_index": twr_index},
        index=dates,
    )
