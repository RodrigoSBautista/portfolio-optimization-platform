"""Optimization tests — properties of each method on seeded synthetic data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core import optimization as opt


@pytest.fixture
def prices():
    # Four assets with increasing volatility (A lowest, D highest), independent.
    rng = np.random.default_rng(0)
    n = 600
    idx = pd.bdate_range("2020-01-01", periods=n)
    vols = {"A": 0.005, "B": 0.010, "C": 0.020, "D": 0.030}
    data = {t: rng.normal(0.0003, v, n) for t, v in vols.items()}
    returns = pd.DataFrame(data, index=idx)
    return 100.0 * (1.0 + returns).cumprod()


def _sums_to_one(w):
    return abs(sum(w.values()) - 1.0) < 1e-6


def _long_only(w):
    return all(v >= -1e-9 for v in w.values())


def _portfolio_variance(prices, w):
    returns = prices.pct_change().dropna()
    cov = returns.cov()
    vec = pd.Series(w).reindex(cov.columns).fillna(0.0).values
    return float(vec @ cov.values @ vec)


# --- baseline -------------------------------------------------------------------

def test_equal_weight():
    w = opt.equal_weight(["AAPL", "msft", "GOOGL"])
    assert set(w) == {"AAPL", "MSFT", "GOOGL"}
    assert all(v == pytest.approx(1 / 3) for v in w.values())


# --- allocation methods ---------------------------------------------------------

def test_inverse_volatility_favours_low_vol(prices):
    w = opt.inverse_volatility(prices)
    assert _sums_to_one(w) and _long_only(w)
    # A is the lowest-vol asset -> should get the most weight; D the least.
    assert w["A"] == max(w.values())
    assert w["D"] == min(w.values())


def test_risk_parity_equalizes_risk_contributions(prices):
    w = opt.risk_parity(prices)
    assert _sums_to_one(w) and all(v > 0 for v in w.values())
    returns = prices.pct_change().dropna()
    cov = returns.cov()
    vec = pd.Series(w).reindex(cov.columns).values
    rc = vec * (cov.values @ vec)  # risk contributions
    # contributions should be close to equal
    assert (rc.max() - rc.min()) / rc.mean() < 0.10


def test_min_variance_beats_equal_weight_variance(prices):
    w = opt.min_variance(prices)
    assert _sums_to_one(w) and _long_only(w)
    eq = opt.equal_weight(list(prices.columns))
    assert _portfolio_variance(prices, w) <= _portfolio_variance(prices, eq) + 1e-12


def test_hrp_valid_and_deterministic(prices):
    w1 = opt.hrp(prices)
    w2 = opt.hrp(prices)
    assert _sums_to_one(w1) and _long_only(w1)
    assert set(w1) == {"A", "B", "C", "D"}
    assert w1 == w2  # deterministic


def test_max_weight_cap_respected(prices):
    w = opt.min_variance(prices, max_weight=0.4)
    assert _sums_to_one(w)
    assert max(w.values()) <= 0.4 + 1e-6


def test_single_asset_gets_full_weight():
    idx = pd.bdate_range("2020-01-01", periods=10)
    prices = pd.DataFrame({"AAPL": np.linspace(100, 110, 10)}, index=idx)
    assert opt.risk_parity(prices) == {"AAPL": 1.0}
    assert opt.hrp(prices) == {"AAPL": 1.0}


# --- selection methods ----------------------------------------------------------

def test_select_low_volatility(prices):
    chosen = opt.select_low_volatility(prices, k=2)
    assert chosen == ["A", "B"]  # the two lowest-vol assets


def test_select_by_clustering_returns_k(prices):
    chosen = opt.select_by_clustering(prices, k=2)
    assert len(chosen) == 2
    assert set(chosen) <= {"A", "B", "C", "D"}


def test_select_clustering_k_ge_universe_returns_all(prices):
    chosen = opt.select_by_clustering(prices, k=10)
    assert set(chosen) == {"A", "B", "C", "D"}


# --- dispatch -------------------------------------------------------------------

def test_allocate_and_select_dispatch(prices):
    for method in opt.ALLOCATION_METHODS:
        w = opt.allocate(method, prices)
        assert _sums_to_one(w) and _long_only(w)
    for method in opt.SELECTION_METHODS:
        assert len(opt.select(method, prices, 2)) == 2


# --- robustness on messy real-world inputs --------------------------------------

def test_methods_survive_nan_gaps_and_flat_assets(prices):
    p = prices.copy()
    p.iloc[5, 0] = np.nan  # internal NaN gap in A (yfinance-style hole)
    p["E"] = 100.0  # flat / zero-variance asset (halted or bad data)
    for method in opt.ALLOCATION_METHODS:
        w = opt.allocate(method, p)
        assert _sums_to_one(w) and _long_only(w)
        assert not any(np.isnan(v) for v in w.values())  # never garbage weights
    for method in opt.SELECTION_METHODS:
        assert len(opt.select(method, p, 2)) >= 1


def test_non_overlapping_histories_are_aligned(prices):
    p = prices.copy()
    p.iloc[:100, 1] = np.nan  # B "lists" ~100 days late
    for method in ("Risk parity", "Minimum-variance", "Hierarchical Risk Parity"):
        w = opt.allocate(method, p)
        assert _sums_to_one(w)
        assert not any(np.isnan(v) for v in w.values())
