"""Curated US ticker universe for search/suggestions in the UI.

Loaded from the committed ``data/tickers.csv`` (S&P 500 + popular ETFs) — a static
snapshot, no network. Free-text tickers are still allowed everywhere; this list only
powers suggestions, so going slightly stale is acceptable (refresh the CSV later).
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

_CSV = Path(__file__).resolve().parent / "tickers.csv"

# Common benchmark choices surfaced first in the benchmark selector.
COMMON_BENCHMARKS = ["SPY", "VOO", "IVV", "VTI", "QQQ", "DIA", "IWM", "VEA", "VWO", "AGG", "BND"]


@lru_cache(maxsize=1)
def load_universe() -> dict[str, str]:
    """Return {symbol: company/fund name} from the committed CSV (cached)."""
    universe: dict[str, str] = {}
    with _CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            symbol = (row.get("symbol") or "").strip().upper()
            if symbol:
                universe[symbol] = (row.get("name") or "").strip()
    return universe


def symbols() -> list[str]:
    """Sorted list of known ticker symbols."""
    return list(load_universe().keys())


def label(symbol: str) -> str:
    """Display label like ``AAPL — Apple Inc.`` (bare symbol if unknown)."""
    name = load_universe().get(symbol.upper())
    return f"{symbol.upper()} — {name}" if name else symbol.upper()
