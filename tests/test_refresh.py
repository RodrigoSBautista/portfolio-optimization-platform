"""Refresh-job tests — spec -> simulation args, and valuation building."""

from __future__ import annotations

import pandas as pd

from core.portfolio import LUMP_SUM, RECURRING, Contribution, Holding, PortfolioSpec
from jobs.refresh import build_valuations


def test_simulation_kwargs_extracts_contributions():
    spec = PortfolioSpec(
        name="p",
        holdings=[Holding("AAPL", 1.0)],
        contributions=[
            Contribution(LUMP_SUM, 1000.0),
            Contribution(RECURRING, 100.0, frequency="monthly"),
        ],
    )
    assert spec.simulation_kwargs() == {
        "lump_sum": 1000.0,
        "recurring_amount": 100.0,
        "recurring_freq": "monthly",
    }


def test_build_valuations_returns_market_and_benchmark():
    idx = pd.date_range("2020-01-02", periods=3, freq="D")
    port = pd.DataFrame({"AAPL": [10.0, 11.0, 12.0]}, index=idx)
    bench = pd.DataFrame({"SPY": [100.0, 101.0, 102.0]}, index=idx)
    spec = PortfolioSpec(
        name="p",
        holdings=[Holding("AAPL", 1.0)],
        benchmark_symbol="SPY",
        contributions=[Contribution(LUMP_SUM, 1000.0)],
    )
    out = build_valuations(spec, port, bench)
    assert list(out.columns) == ["market_value", "benchmark_value"]
    assert len(out) == 3
    assert out["market_value"].iloc[0] == 1000.0  # lump sum on day one
    assert out["market_value"].iloc[-1] == 1200.0  # 100 shares * 12
