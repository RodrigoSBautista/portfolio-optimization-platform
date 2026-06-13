"""Market-data provider: a thin, swappable wrapper around yfinance.

Returns **dividend- and split-adjusted** close prices (a total-return proxy) so
historical growth is not understated. The source is hidden behind the small
``PriceProvider`` protocol, so it can be replaced later without touching ``core/``.

Data-robustness helpers (delisted tickers, non-overlapping histories) live here —
never in ``core/``.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class PriceProvider(Protocol):
    """Anything that can return adjusted close prices for a set of tickers."""

    def fetch_adjusted_close(
        self, tickers: list[str], start: date, end: date | None = None
    ) -> pd.DataFrame:
        """Return a DataFrame indexed by date, one column per ticker."""
        ...


class YFinanceProvider:
    """Fetches split/dividend-adjusted close prices via yfinance."""

    def fetch_adjusted_close(
        self, tickers: list[str], start: date, end: date | None = None
    ) -> pd.DataFrame:
        if not tickers:
            return pd.DataFrame()

        import yfinance as yf

        raw = yf.download(
            tickers=list(tickers),
            start=start,
            end=end,
            auto_adjust=True,  # adjust for splits AND dividends (total-return proxy)
            progress=False,
            actions=False,
        )
        return _extract_close(raw, tickers)


def _extract_close(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Normalise yfinance output (single- or multi-ticker) to a [date x ticker] frame."""
    if raw is None or raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        # Multi-ticker: top level is the field name; take the "Close" block.
        close = raw["Close"].copy()
    else:
        # Single ticker: flat columns (Open/High/Low/Close/Volume).
        close = raw[["Close"]].copy()
        close.columns = [tickers[0].upper()]

    close.columns = [str(c).upper() for c in close.columns]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close.index.name = "date"

    # Preserve requested order; silently omit tickers that returned nothing.
    present = [t.upper() for t in tickers if t.upper() in close.columns]
    return close[present]


def drop_empty_tickers(prices: pd.DataFrame) -> pd.DataFrame:
    """Remove columns that are entirely NaN — i.e. delisted/invalid tickers."""
    return prices.dropna(axis=1, how="all")


def common_history(prices: pd.DataFrame) -> pd.DataFrame:
    """Trim to the window where *every* remaining ticker has data.

    Guards against look-ahead from non-overlapping histories: the result starts no
    earlier than the latest ticker's first trading day and ends no later than the
    earliest ticker's last trading day. Internal gaps are forward-filled (uses only
    past data, so it stays look-ahead-safe).
    """
    prices = drop_empty_tickers(prices)
    if prices.empty:
        return prices

    firsts = [prices[c].first_valid_index() for c in prices.columns]
    lasts = [prices[c].last_valid_index() for c in prices.columns]
    start, end = max(firsts), min(lasts)
    if start is None or end is None or start > end:
        return prices.iloc[0:0]

    # Forward-fill before trimming so a gap on the boundary day fills from prior real
    # data (ffill only uses the past, so this stays look-ahead-safe).
    return prices.ffill().loc[start:end]
