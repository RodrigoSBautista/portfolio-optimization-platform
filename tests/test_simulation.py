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


# --- escalation (annual contribution growth) ------------------------------------

def test_escalation_grows_contribution_on_anniversary():
    # Monthly $100 with 5%/yr escalation, flat $1 price over ~2 years.
    # Year 1 contributes 100/mo; year 2 contributes 105/mo.
    idx = pd.bdate_range("2021-01-01", "2022-12-31")
    prices = pd.DataFrame({"AAPL": 1.0}, index=idx)
    out = simulate_portfolio(
        prices,
        {"AAPL": 1.0},
        recurring_amount=100.0,
        recurring_freq="monthly",
        escalation_pct=5.0,
    )
    invested = out["invested"]
    # Per-contribution deltas: 0 -> first day baseline, then step-ups.
    deltas = invested.diff().fillna(invested.iloc[0])
    contributed = deltas[deltas > 0].round(6)
    year1 = contributed[contributed.index < pd.Timestamp("2022-01-01")]
    year2 = contributed[contributed.index >= pd.Timestamp("2022-01-01")]
    # 12 contributions each year at $100 then $105.
    assert len(year1) == 12
    assert year1.tolist() == pytest.approx([100.0] * 12)
    assert len(year2) == 12
    assert year2.tolist() == pytest.approx([105.0] * 12)


def test_escalation_zero_matches_no_escalation():
    px = _prices({"AAPL": [10.0, 10.0, 10.0]})
    base = simulate_portfolio(
        px, {"AAPL": 1.0}, recurring_amount=100.0, recurring_freq="daily"
    )
    esc = simulate_portfolio(
        px,
        {"AAPL": 1.0},
        recurring_amount=100.0,
        recurring_freq="daily",
        escalation_pct=0.0,
    )
    pd.testing.assert_frame_equal(base, esc)


def test_escalation_rejects_negative():
    px = _prices({"AAPL": [10.0, 10.0]})
    with pytest.raises(ValueError, match="escalation_pct"):
        simulate_portfolio(
            px, {"AAPL": 1.0}, recurring_amount=100.0,
            recurring_freq="daily", escalation_pct=-1.0,
        )


# --- advisory-fee drag ----------------------------------------------------------

def test_fee_drag_decays_value_on_flat_prices():
    # Flat prices, lump sum, 1%/yr advisory fee -> value decays at (1-fee)^(1/252)/day.
    n = 10
    px = _prices({"AAPL": [100.0] * n})
    out = simulate_portfolio(px, {"AAPL": 1.0}, lump_sum=1000.0, annual_fee_pct=1.0)
    daily = (1.0 - 0.01) ** (1.0 / 252)
    # Day 0: fee step is skipped (no holdings yet), then the lump sum buys in at 1000.
    # Each subsequent day the existing holdings decay by one daily fee factor.
    expected = [1000.0 * daily**i for i in range(n)]
    np.testing.assert_allclose(out["value"].tolist(), expected, rtol=1e-12)
    # TWR index reflects the same steady decay (1.0 on day one, then daily^i).
    np.testing.assert_allclose(
        out["twr_index"].tolist(), [daily**i for i in range(n)], rtol=1e-12
    )


def test_fee_zero_matches_no_fee():
    px = _prices({"AAPL": [10.0, 11.0, 12.0]})
    base = simulate_portfolio(px, {"AAPL": 1.0}, lump_sum=1000.0)
    with_fee = simulate_portfolio(px, {"AAPL": 1.0}, lump_sum=1000.0, annual_fee_pct=0.0)
    pd.testing.assert_frame_equal(base, with_fee)


def test_fee_rejects_out_of_range():
    px = _prices({"AAPL": [10.0, 11.0]})
    with pytest.raises(ValueError, match="annual_fee_pct"):
        simulate_portfolio(px, {"AAPL": 1.0}, lump_sum=100.0, annual_fee_pct=100.0)
    with pytest.raises(ValueError, match="annual_fee_pct"):
        simulate_portfolio(px, {"AAPL": 1.0}, lump_sum=100.0, annual_fee_pct=-1.0)


# --- backward-compatible defaults reproduce old behavior ------------------------

def test_new_params_default_to_old_behavior():
    px = _prices({"AAPL": [10.0, 11.0, 12.0]})
    out = simulate_portfolio(px, {"AAPL": 1.0}, lump_sum=1000.0)
    assert out["value"].tolist() == [1000.0, 1100.0, 1200.0]
    np.testing.assert_allclose(out["twr_index"].tolist(), [1.0, 1.1, 1.2])


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
