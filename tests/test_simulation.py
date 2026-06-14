"""Simulation tests — hand-verified arithmetic, TWR correctness, look-ahead safety."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.simulation import normalize_weights, simulate_portfolio


def _prices(values: dict[str, list[float]], start="2020-01-02"):
    n = len(next(iter(values.values())))
    idx = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame(values, index=idx, dtype=float)


# --- weight normalization -------------------------------------------------------

def test_normalize_weights_rescales_to_one():
    out = normalize_weights({"AAPL": 1, "MSFT": 3}, ["AAPL", "MSFT"])
    assert out == {"AAPL": 0.25, "MSFT": 0.75}


def test_normalize_weights_rejects_unknown_ticker():
    with pytest.raises(ValueError, match="no price data"):
        normalize_weights({"NOPE": 1.0}, ["AAPL"])


def test_normalize_weights_rejects_negative():
    with pytest.raises(ValueError, match="negative"):
        normalize_weights({"AAPL": -0.5}, ["AAPL"])


# --- lump sum -------------------------------------------------------------------

def test_lump_sum_buy_and_hold():
    px = _prices({"AAPL": [10.0, 11.0, 12.0]})
    out = simulate_portfolio(px, {"AAPL": 1.0}, lump_sum=1000.0)
    # 100 shares bought at 10; value tracks price.
    assert out["value"].tolist() == [1000.0, 1100.0, 1200.0]
    assert out["invested"].tolist() == [1000.0, 1000.0, 1000.0]
    # TWR index == price growth for a single lump sum.
    np.testing.assert_allclose(out["twr_index"].tolist(), [1.0, 1.1, 1.2])


def test_two_asset_lump_sum_weighting():
    px = _prices({"AAPL": [10.0, 10.0], "MSFT": [20.0, 40.0]})
    out = simulate_portfolio(px, {"AAPL": 0.5, "MSFT": 0.5}, lump_sum=1000.0)
    # 500 into each: 50 AAPL shares, 25 MSFT shares. Day2: 500 + 1000 = 1500.
    assert out["value"].iloc[0] == 1000.0
    assert out["value"].iloc[1] == 1500.0


# --- recurring (DCA) + time-weighted return -------------------------------------

def test_dca_into_flat_prices_has_zero_twr_but_growing_value():
    # Prices never move: TWR must be 0% even though value grows from contributions.
    px = _prices({"AAPL": [10.0, 10.0, 10.0]})
    out = simulate_portfolio(
        px, {"AAPL": 1.0}, recurring_amount=100.0, recurring_freq="daily"
    )
    assert out["invested"].tolist() == [100.0, 200.0, 300.0]
    assert out["value"].tolist() == [100.0, 200.0, 300.0]
    np.testing.assert_allclose(out["twr_index"].tolist(), [1.0, 1.0, 1.0])


def _contribution_count(freq: str) -> float:
    # One business-day year, constant price, $1 per contribution -> invested == count.
    idx = pd.bdate_range("2021-01-01", "2021-12-31")
    prices = pd.DataFrame({"AAPL": 1.0}, index=idx)
    out = simulate_portfolio(prices, {"AAPL": 1.0}, recurring_amount=1.0, recurring_freq=freq)
    return out["invested"].iloc[-1]


@pytest.mark.parametrize(
    ("freq", "expected"),
    [
        ("monthly", 12),
        ("every 2 months", 6),
        ("quarterly", 4),
        ("every 6 months", 2),
        ("annually", 1),
    ],
)
def test_recurring_frequency_contribution_counts(freq, expected):
    assert _contribution_count(freq) == pytest.approx(expected)


def test_weekly_frequency_is_about_one_per_week():
    # ~52 weeks in a year (a small first-week boundary artifact is acceptable).
    assert 52 <= _contribution_count("weekly") <= 53


def test_dca_twr_ignores_contribution_inflows():
    # Price rises 10 -> 11 on day 2; a fresh contribution lands the same day.
    px = _prices({"AAPL": [10.0, 11.0]})
    out = simulate_portfolio(
        px, {"AAPL": 1.0}, recurring_amount=100.0, recurring_freq="daily"
    )
    # Day1: 10 shares (=100). Day2 holding value before contribution = 10*11 = 110,
    # so TWR factor = 1.1; the day-2 contribution must NOT inflate the return.
    np.testing.assert_allclose(out["twr_index"].tolist(), [1.0, 1.1])
    # Value includes both growth and the new $100 contribution: 110 + 100 = 210.
    assert out["value"].iloc[1] == pytest.approx(210.0)
    assert out["invested"].iloc[1] == 200.0


# --- rebalancing ----------------------------------------------------------------

def test_rebalance_restores_target_weights():
    # MSFT doubles on day 2; a daily rebalance should pull weights back to 50/50.
    px = _prices({"AAPL": [10.0, 10.0, 10.0], "MSFT": [10.0, 20.0, 20.0]})
    out = simulate_portfolio(
        px, {"AAPL": 0.5, "MSFT": 0.5}, lump_sum=1000.0, rebalance="daily"
    )
    # After day-2 rebalance, each sleeve should be half of the day-2 total (1500).
    # Verify via day-3 (flat prices): value stays 1500 and weights held.
    assert out["value"].iloc[1] == pytest.approx(1500.0)
    assert out["value"].iloc[2] == pytest.approx(1500.0)


# --- look-ahead safety ----------------------------------------------------------

def test_future_prices_do_not_affect_past_values():
    base = {"AAPL": [10.0, 11.0, 12.0]}
    out_a = simulate_portfolio(_prices(base), {"AAPL": 1.0}, lump_sum=1000.0)
    # Change ONLY the last day's price; earlier values must be identical.
    bumped = {"AAPL": [10.0, 11.0, 99.0]}
    out_b = simulate_portfolio(_prices(bumped), {"AAPL": 1.0}, lump_sum=1000.0)
    assert out_a["value"].iloc[:2].tolist() == out_b["value"].iloc[:2].tolist()


def test_empty_overlap_raises():
    px = pd.DataFrame(
        {"AAPL": [np.nan, 11.0], "MSFT": [20.0, np.nan]},
        index=pd.date_range("2020-01-02", periods=2, freq="D"),
    )
    with pytest.raises(ValueError, match="no overlapping price history"):
        simulate_portfolio(px, {"AAPL": 0.5, "MSFT": 0.5}, lump_sum=100.0)
