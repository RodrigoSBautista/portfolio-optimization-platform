"""Refresh-job tests — spec -> simulation args, and valuation building."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from core.portfolio import LUMP_SUM, RECURRING, Contribution, Holding, PortfolioSpec
from data.prices import PriceService
from jobs.refresh import build_valuations, refresh_portfolio
from storage.db import make_session_factory
from storage.models import Base
from storage.repository import Repository


class _FakeProvider:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def fetch_adjusted_close(self, tickers, start, end=None):
        cols = [t for t in tickers if t in self.data.columns]
        return self.data[cols]


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


def test_refresh_portfolio_aligns_histories_and_is_idempotent():
    # AAPL lists two days after SPY -> the common (aligned) window is 3 days.
    idx = pd.date_range("2020-01-02", periods=5, freq="D")
    data = pd.DataFrame(
        {
            "AAPL": [np.nan, np.nan, 10.0, 11.0, 12.0],
            "SPY": [100.0, 101.0, 102.0, 103.0, 104.0],
        },
        index=idx,
    )
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    repo = Repository(session)
    user = repo.create_user("a", "h")
    spec = PortfolioSpec(
        name="p",
        holdings=[Holding("AAPL", 1.0)],
        benchmark_symbol="SPY",
        contributions=[Contribution(LUMP_SUM, 1000.0)],
    )
    portfolio = repo.save_portfolio(user.id, spec)
    service = PriceService(provider=_FakeProvider(data), cache=None)

    written = refresh_portfolio(repo, service, user.id, portfolio.id, spec, date(2020, 1, 1))
    vals = repo.get_valuations(user.id, portfolio.id)
    assert written == 3  # aligned to AAPL's 3-day overlap with SPY
    assert len(vals) == 3
    assert vals[0].market_value == 1000.0  # lump sum on the first aligned day
    assert vals[0].benchmark_value is not None  # benchmark stored on the same dates

    # Re-running upserts in place — no duplicate rows.
    again = refresh_portfolio(repo, service, user.id, portfolio.id, spec, date(2020, 1, 1))
    assert again == 3
    assert len(repo.get_valuations(user.id, portfolio.id)) == 3
    session.close()
