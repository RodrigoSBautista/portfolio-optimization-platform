"""Tests for the shared simulation runner (used by Simulation + Compare pages)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.sim_runner import SimError, format_metrics, run_simulation
from core.portfolio import LUMP_SUM, Contribution, Holding, PortfolioSpec
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


def test_format_metrics_keys():
    idx = pd.Series([1.0, 1.1, 1.2], index=pd.date_range("2020-01-01", periods=3))
    out = format_metrics(idx)
    assert set(out) == {"Total return", "CAGR", "Volatility (ann.)", "Sharpe", "Max drawdown"}
