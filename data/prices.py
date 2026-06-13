"""High-level price access: combine a provider with the parquet cache.

``PriceService`` is the single entry point ``core/`` and ``jobs/`` use to obtain
adjusted close prices. The provider and cache are injectable so tests can run fully
offline.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from data.cache import ParquetPriceCache
from data.provider import PriceProvider, YFinanceProvider


class PriceService:
    def __init__(
        self,
        provider: PriceProvider | None = None,
        cache: ParquetPriceCache | None = None,
    ) -> None:
        self.provider = provider or YFinanceProvider()
        self.cache = cache

    def get_adjusted_close(
        self,
        tickers: list[str],
        start: date,
        end: date | None = None,
        *,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Return a [date x ticker] frame of adjusted close prices for the window.

        On a cache hit that covers ``start`` the cached series is reused; otherwise
        the ticker is (re)fetched and the cache is refreshed. Tickers that return no
        data (delisted/invalid) are silently omitted.
        """
        wanted = [t.upper() for t in tickers]
        series_by_ticker: dict[str, pd.Series] = {}
        to_fetch: list[str] = []

        for ticker in wanted:
            cached = self._load_cached(ticker, start) if use_cache else None
            if cached is not None:
                series_by_ticker[ticker] = cached
            else:
                to_fetch.append(ticker)

        if to_fetch:
            fetched = self.provider.fetch_adjusted_close(to_fetch, start, end)
            for ticker in to_fetch:
                if ticker in fetched.columns:
                    series = fetched[ticker].dropna()
                    if series.empty:
                        continue
                    series_by_ticker[ticker] = series
                    if use_cache and self.cache is not None:
                        self.cache.save(ticker, series)

        if not series_by_ticker:
            return pd.DataFrame()

        prices = pd.DataFrame(series_by_ticker).sort_index()
        prices = prices.loc[prices.index >= pd.Timestamp(start)]
        if end is not None:
            prices = prices.loc[prices.index <= pd.Timestamp(end)]
        ordered = [t for t in wanted if t in prices.columns]
        return prices[ordered]

    def _load_cached(self, ticker: str, start: date) -> pd.Series | None:
        if self.cache is None:
            return None
        series = self.cache.load(ticker)
        if series is None or series.empty:
            return None
        # Reject a cache entry that starts after the requested window (would silently
        # truncate a backtest); refetch instead.
        if series.index.min() > pd.Timestamp(start):
            return None
        return series
