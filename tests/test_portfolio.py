"""Tests for portfolio value-object helpers."""

from __future__ import annotations

from datetime import date

from core.portfolio import (
    SPEC_VERSION,
    Holding,
    Lot,
    PortfolioSpec,
    weights_from_amounts,
)


def test_weights_from_amounts_normalizes():
    weights, total = weights_from_amounts({"AAPL": 600, "MSFT": 400})
    assert total == 1000
    assert weights == {"AAPL": 0.6, "MSFT": 0.4}


def test_weights_from_amounts_ignores_nonpositive():
    weights, total = weights_from_amounts({"AAPL": 100, "MSFT": 0, "X": -5})
    assert total == 100
    assert weights == {"AAPL": 1.0}


def test_weights_from_amounts_uppercases_symbols():
    weights, _ = weights_from_amounts({"aapl": 50, "msft": 50})
    assert set(weights) == {"AAPL", "MSFT"}


def test_weights_from_amounts_empty():
    assert weights_from_amounts({}) == ({}, 0.0)


# --- lot-based spec: serialization + backward compatibility ---------------------

def test_spec_version_is_2():
    assert SPEC_VERSION == 2


def test_is_lot_based_property():
    assert not PortfolioSpec(name="p").is_lot_based
    spec = PortfolioSpec(name="p", lots=[Lot("aapl", date(2020, 1, 2), 100.0)])
    assert spec.is_lot_based


def test_v1_payload_without_lots_loads_and_has_empty_lots():
    # A v1 export (no "lots" key) must still load; lots default to empty.
    v1 = {
        "version": 1,
        "name": "legacy",
        "benchmark_symbol": "SPY",
        "base_currency": "USD",
        "holdings": [{"symbol": "AAPL", "weight": 1.0}],
        "contributions": [],
    }
    spec = PortfolioSpec.from_dict(v1)
    assert spec.lots == []
    assert not spec.is_lot_based
    assert spec.holdings == [Holding("AAPL", 1.0)]


def test_v1_spec_roundtrips_through_v2_serialization():
    spec = PortfolioSpec(name="legacy", holdings=[Holding("AAPL", 1.0)])
    restored = PortfolioSpec.from_dict(spec.to_dict())
    assert restored == spec
    assert restored.to_dict()["lots"] == []


def test_v2_spec_with_lots_roundtrips_exactly():
    spec = PortfolioSpec(
        name="dca",
        lots=[
            Lot("AAPL", date(2020, 1, 2), 1000.0),
            Lot("MSFT", date(2021, 6, 15), 500.0),
        ],
    )
    payload = spec.to_dict()
    assert payload["version"] == 2
    assert payload["lots"] == [
        {"symbol": "AAPL", "date": "2020-01-02", "amount": 1000.0},
        {"symbol": "MSFT", "date": "2021-06-15", "amount": 500.0},
    ]
    assert PortfolioSpec.from_dict(payload) == spec


def test_to_dict_uppercases_lot_symbols():
    spec = PortfolioSpec(name="p", lots=[Lot("aapl", date(2020, 1, 2), 100.0)])
    assert spec.to_dict()["lots"][0]["symbol"] == "AAPL"


def test_from_dict_ignores_unknown_future_keys():
    payload = {
        "version": 99,
        "name": "future",
        "lots": [{"symbol": "AAPL", "date": "2020-01-02", "amount": 100.0}],
        "some_future_field": {"nested": True},
    }
    spec = PortfolioSpec.from_dict(payload)
    assert spec.lots == [Lot("AAPL", date(2020, 1, 2), 100.0)]
