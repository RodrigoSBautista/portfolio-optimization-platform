"""Tests for portfolio value-object helpers."""

from __future__ import annotations

from core.portfolio import weights_from_amounts


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
