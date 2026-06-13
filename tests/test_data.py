"""Data-layer tests — run fully offline with a fake provider and a tmp-dir cache."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from data.cache import ParquetPriceCache
from data.prices import PriceService
from data.provider import (
    _extract_close,
    common_history,
    drop_empty_tickers,
)


def _frame(index, **columns):
    return pd.DataFrame(columns, index=pd.to_datetime(index))


class FakeProvider:
    """Records calls and returns canned adjusted-close data."""

    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.calls: list[list[str]] = []

    def fetch_adjusted_close(self, tickers, start, end=None):
        self.calls.append(list(tickers))
        cols = [t for t in tickers if t in self.data.columns]
        return self.data[cols]


# --- _extract_close -------------------------------------------------------------

def test_extract_close_single_ticker():
    raw = _frame(["2020-01-02", "2020-01-03"], Open=[1, 2], Close=[10.0, 11.0])
    out = _extract_close(raw, ["aapl"])
    assert list(out.columns) == ["AAPL"]
    assert out["AAPL"].tolist() == [10.0, 11.0]
    assert out.index.name == "date"


def test_extract_close_multi_ticker():
    cols = pd.MultiIndex.from_product([["Close", "Open"], ["AAPL", "MSFT"]])
    raw = pd.DataFrame(
        [[10.0, 20.0, 1, 2], [11.0, 21.0, 3, 4]],
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        columns=cols,
    )
    out = _extract_close(raw, ["AAPL", "MSFT"])
    assert list(out.columns) == ["AAPL", "MSFT"]
    assert out["MSFT"].tolist() == [20.0, 21.0]


def test_extract_close_empty():
    assert _extract_close(pd.DataFrame(), ["AAPL"]).empty


# --- cleaning utilities ---------------------------------------------------------

def test_drop_empty_tickers_removes_all_nan_column():
    prices = _frame(
        ["2020-01-02", "2020-01-03"],
        AAPL=[10.0, 11.0],
        DEAD=[np.nan, np.nan],
    )
    out = drop_empty_tickers(prices)
    assert list(out.columns) == ["AAPL"]


def test_common_history_trims_to_overlap_and_ffills():
    # MSFT starts a day late; AAPL has an internal gap.
    prices = _frame(
        ["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"],
        AAPL=[10.0, np.nan, 12.0, 13.0],
        MSFT=[np.nan, 21.0, 22.0, 23.0],
    )
    out = common_history(prices)
    # Trimmed to MSFT's first valid day onward.
    assert out.index.min() == pd.Timestamp("2020-01-03")
    # AAPL's internal NaN forward-filled from the prior value.
    assert out.loc[pd.Timestamp("2020-01-03"), "AAPL"] == 10.0
    assert not out.isna().any().any()


# --- PriceService: cache miss/hit/coverage --------------------------------------

@pytest.fixture
def sample_data():
    idx = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"])
    return _frame(idx, AAPL=[10.0, 11.0, 12.0], MSFT=[20.0, 21.0, 22.0])


def test_service_fetches_then_caches(tmp_path, sample_data):
    provider = FakeProvider(sample_data)
    cache = ParquetPriceCache(tmp_path)
    service = PriceService(provider=provider, cache=cache)

    out = service.get_adjusted_close(["AAPL", "MSFT"], date(2020, 1, 1))
    assert list(out.columns) == ["AAPL", "MSFT"]
    assert out.shape == (3, 2)
    assert provider.calls == [["AAPL", "MSFT"]]
    # Cache files written.
    assert cache.load("AAPL") is not None


def test_service_uses_cache_on_second_call(tmp_path, sample_data):
    provider = FakeProvider(sample_data)
    cache = ParquetPriceCache(tmp_path)
    service = PriceService(provider=provider, cache=cache)

    # Use the real first trading day so the coverage check is unambiguous.
    service.get_adjusted_close(["AAPL"], date(2020, 1, 2))
    provider.calls.clear()
    out = service.get_adjusted_close(["AAPL"], date(2020, 1, 2))

    assert provider.calls == []  # served from cache, no refetch
    assert out["AAPL"].tolist() == [10.0, 11.0, 12.0]


def test_service_refetches_when_cache_starts_too_late(tmp_path, sample_data):
    provider = FakeProvider(sample_data)
    cache = ParquetPriceCache(tmp_path)
    service = PriceService(provider=provider, cache=cache)

    # Seed cache with a series that only starts 2020-01-03 (truncated history).
    cache.save("AAPL", sample_data["AAPL"].iloc[1:])
    provider.calls.clear()

    # Requesting from the real first trading day exposes the coverage gap.
    service.get_adjusted_close(["AAPL"], date(2020, 1, 2))
    assert provider.calls == [["AAPL"]]  # coverage gap -> refetch


def test_service_omits_unknown_ticker(tmp_path, sample_data):
    provider = FakeProvider(sample_data)
    service = PriceService(provider=provider, cache=ParquetPriceCache(tmp_path))

    out = service.get_adjusted_close(["AAPL", "NOPE"], date(2020, 1, 1))
    assert list(out.columns) == ["AAPL"]


def test_service_slices_to_window(tmp_path, sample_data):
    provider = FakeProvider(sample_data)
    service = PriceService(provider=provider, cache=ParquetPriceCache(tmp_path))

    out = service.get_adjusted_close(
        ["AAPL"], date(2020, 1, 3), date(2020, 1, 3)
    )
    assert out.index.tolist() == [pd.Timestamp("2020-01-03")]
