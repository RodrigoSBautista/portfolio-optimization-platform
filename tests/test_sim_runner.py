"""Tests for the shared simulation runner (used by Simulation + Compare pages)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.sim_runner import SimError, format_metrics, run_simulation
from core.portfolio import LUMP_SUM, Contribution, Holding, Lot, PortfolioSpec
from data.provider import common_history


def _spec(name, symbol, benchmark="SPY"):
    return PortfolioSpec(
        name=name,
        holdings=[Holding(symbol, 1.0)],
        benchmark_symbol=benchmark,
        contributions=[Contribution(LUMP_SUM, 1000.0)],
    )


def test_run_simulation_basic():
    idx = pd.date_range("2020-01-02", periods=3, freq="D")
    prices = pd.DataFrame({"AAPL": [10.0, 11.0, 12.0], "SPY": [100.0, 101.0, 102.0]}, index=idx)
    res = run_simulation(_spec("p", "AAPL"), prices)
    assert res.final_value == 1200.0  # 100 shares * 12
    assert res.invested == 1000.0
    assert res.has_benchmark and res.benchmark_value is not None
    assert res.dropped == []


def test_run_simulation_benchmark_override():
    idx = pd.date_range("2020-01-02", periods=2, freq="D")
    prices = pd.DataFrame(
        {"AAPL": [10.0, 11.0], "SPY": [100.0, 101.0], "QQQ": [50.0, 60.0]}, index=idx
    )
    res = run_simulation(_spec("p", "AAPL", benchmark="SPY"), prices, benchmark="QQQ")
    assert res.benchmark == "QQQ"
    # QQQ +20% -> benchmark value 1000 -> 1200
    assert res.benchmark_value.iloc[-1] == pytest.approx(1200.0)


def test_run_simulation_raises_without_holdings_data():
    prices = pd.DataFrame({"SPY": [100.0, 101.0]}, index=pd.date_range("2020-01-02", periods=2))
    with pytest.raises(SimError):
        run_simulation(_spec("p", "AAPL"), prices)


def test_compare_portfolios_share_one_window():
    # MSFT lists two days after AAPL/SPY -> a global align gives both a 3-day window.
    idx = pd.date_range("2020-01-02", periods=5, freq="D")
    prices = pd.DataFrame(
        {
            "AAPL": [10.0, 11.0, 12.0, 13.0, 14.0],
            "MSFT": [np.nan, np.nan, 20.0, 21.0, 22.0],
            "SPY": [100.0, 101.0, 102.0, 103.0, 104.0],
        },
        index=idx,
    )
    aligned = common_history(prices)  # intersection window across ALL columns
    r1 = run_simulation(_spec("p1", "AAPL"), aligned, benchmark="SPY")
    r2 = run_simulation(_spec("p2", "MSFT"), aligned, benchmark="SPY")
    assert list(r1.sim.index) == list(r2.sim.index)  # same shared window
    assert r1.invested == r2.invested == 1000.0


def test_run_simulation_portfolio_holding_its_own_benchmark():
    # Regression: holdings that include the benchmark (SPY vs SPY) used to duplicate
    # the column and make the benchmark slice 2-D.
    idx = pd.date_range("2020-01-02", periods=3, freq="D")
    prices = pd.DataFrame(
        {"SPY": [100.0, 101.0, 102.0], "AGG": [50.0, 50.0, 50.0]}, index=idx
    )
    spec = PortfolioSpec(
        name="p",
        holdings=[Holding("SPY", 0.5), Holding("AGG", 0.5)],
        benchmark_symbol="SPY",
        contributions=[Contribution(LUMP_SUM, 1000.0)],
    )
    res = run_simulation(spec, prices)
    assert res.has_benchmark
    assert res.benchmark_value.ndim == 1  # 1-D series, not a 2-D slice
    assert res.benchmark_value.iloc[-1] == pytest.approx(1020.0)  # SPY +2%


# --- lot-based branch -----------------------------------------------------------


def _lot_prices():
    idx = pd.date_range("2021-01-04", periods=3, freq="B")
    return pd.DataFrame(
        {"AAPL": [10.0, 11.0, 12.0], "SPY": [100.0, 110.0, 120.0]}, index=idx
    )


def test_run_simulation_lot_branch_exact_values_and_dropped():
    # AAPL: 1000$ on day 0 -> 100 shares; value 1000/1100/1200. ZZZZ has no price data
    # (dropped) and is excluded from BOTH the portfolio and the benchmark mirror flows.
    spec = PortfolioSpec(
        name="Lots",
        benchmark_symbol="SPY",
        lots=[
            Lot("AAPL", date(2021, 1, 4), 1000.0),
            Lot("ZZZZ", date(2021, 1, 4), 500.0),
        ],
    )
    res = run_simulation(spec, _lot_prices())
    assert res.invested == pytest.approx(1000.0)
    assert res.final_value == pytest.approx(1200.0)
    assert list(res.sim["value"]) == pytest.approx([1000.0, 1100.0, 1200.0])
    assert res.dropped == ["ZZZZ"]  # symbol with no price data surfaced

    # Benchmark uses MIRROR lots: the SAME placed dollars (1000$) into SPY on the same
    # day -> day-0 value equals the invested amount (equal flows), grows with SPY.
    assert res.has_benchmark
    assert res.benchmark_value.iloc[0] == pytest.approx(1000.0)
    assert res.benchmark_value.iloc[-1] == pytest.approx(1200.0)  # SPY +20%
    assert list(res.benchmark_value.index) == list(res.sim.index)  # aligned windows


def test_run_simulation_lot_branch_rejects_weight_overrides():
    spec = PortfolioSpec(
        name="Lots",
        benchmark_symbol="SPY",
        lots=[Lot("AAPL", date(2021, 1, 4), 1000.0)],
    )
    prices = _lot_prices()
    for override in ({"annual_fee_pct": 1.0}, {"rebalance": "monthly"}, {"escalation_pct": 5.0}):
        with pytest.raises(SimError):
            run_simulation(spec, prices, sim_overrides=override)
    # Trivial (zero/None) overrides are fine — they simply don't apply.
    trivial = {"annual_fee_pct": 0.0, "rebalance": None, "escalation_pct": 0.0}
    ok = run_simulation(spec, prices, sim_overrides=trivial)
    assert ok.final_value == pytest.approx(1200.0)


def test_format_metrics_keys():
    idx = pd.Series([1.0, 1.1, 1.2], index=pd.date_range("2020-01-01", periods=3))
    out = format_metrics(idx)
    # Original five rows plus the always-appended risk-adjusted extras. Beta/Alpha only
    # appear when a benchmark_index is supplied (not here).
    assert set(out) == {
        "Total return", "CAGR", "Volatility (ann.)", "Sharpe", "Max drawdown",
        "Sortino", "Calmar", "Best year", "Worst year",
    }
    assert "Beta" not in out


def test_format_metrics_adds_beta_alpha_with_benchmark():
    idx = pd.Series([1.0, 1.05, 1.1, 1.2], index=pd.date_range("2020-01-01", periods=4))
    bench = pd.Series([1.0, 1.02, 1.05, 1.08], index=idx.index)
    out = format_metrics(idx, benchmark_index=bench)
    assert {"Beta", "Alpha (ann.)"} <= set(out)


def test_lot_benchmark_invested_parity_when_benchmark_lists_late():
    # Regression (review B1): a benchmark that listed AFTER an early lot must still
    # receive every dollar — the early mirror buy is clamped to the benchmark's first
    # trading day, not dropped (which would fake outperformance).
    idx = pd.date_range("2020-01-02", periods=5, freq="B")  # Thu,Fri,Mon,Tue,Wed
    prices = pd.DataFrame(
        {
            "AAPL": [10.0, 10.0, 10.0, 10.0, 10.0],  # flat -> value == invested
            "SPY": [np.nan, np.nan, 100.0, 100.0, 100.0],  # lists on day 3 (Jan 6)
        },
        index=idx,
    )
    spec = PortfolioSpec(
        name="p",
        benchmark_symbol="SPY",
        lots=[
            Lot("AAPL", date(2020, 1, 2), 1000.0),  # before SPY exists
            Lot("AAPL", date(2020, 1, 6), 500.0),
        ],
    )
    res = run_simulation(spec, prices)
    # Portfolio invested the full $1500 (flat AAPL -> value 1500 too).
    assert res.sim["invested"].iloc[-1] == pytest.approx(1500.0)
    assert res.sim["value"].iloc[-1] == pytest.approx(1500.0)
    # Benchmark received the full $1500 (both mirror buys, the early one clamped to
    # SPY's first day) -> flat SPY value 1500. The bug reported ~500 (dollars dropped).
    assert res.benchmark_value.iloc[-1] == pytest.approx(1500.0)
