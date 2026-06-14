"""Ticker-universe loader tests."""

from __future__ import annotations

from data import tickers


def test_universe_loads_and_has_known_symbols():
    universe = tickers.load_universe()
    assert len(universe) > 400
    assert "AAPL" in universe
    assert "SPY" in universe


def test_symbols_are_upper_and_nonblank():
    syms = tickers.symbols()
    assert all(s and s == s.upper() for s in syms)
    # class shares are normalized to '-' (yfinance style)
    assert "BRK-B" in syms


def test_label_formats_known_and_unknown():
    assert tickers.label("aapl").startswith("AAPL — ")
    assert tickers.label("ZZZZ") == "ZZZZ"


def test_common_benchmarks_are_in_universe():
    universe = tickers.load_universe()
    assert all(b in universe for b in tickers.COMMON_BENCHMARKS)
