"""Parquet cache for adjusted prices, with a per-ticker "last refreshed" marker.

Cached price files are data artifacts, never committed (see ``.gitignore``:
``data/cache/`` and ``*.parquet``). The cache survives outages and cuts repeat calls
to the market-data source.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

DEFAULT_CACHE_DIR = Path("data/cache")
_COLUMN = "adj_close"


class ParquetPriceCache:
    """Stores one adjusted-close series per ticker as ``<TICKER>.parquet``."""

    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR) -> None:
        self.cache_dir = Path(cache_dir)

    def _path(self, ticker: str) -> Path:
        return self.cache_dir / f"{ticker.upper()}.parquet"

    def load(self, ticker: str) -> pd.Series | None:
        path = self._path(ticker)
        if not path.exists():
            return None
        df = pd.read_parquet(path)
        series = df[_COLUMN]
        series.index = pd.to_datetime(series.index)
        series.name = ticker.upper()
        return series

    def save(self, ticker: str, series: pd.Series) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        frame = series.rename(_COLUMN).to_frame()
        frame.index.name = "date"
        frame.to_parquet(self._path(ticker))

    def last_refreshed(self, ticker: str) -> datetime | None:
        """UTC timestamp of the cache file's last write, or None if uncached."""
        path = self._path(ticker)
        if not path.exists():
            return None
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
