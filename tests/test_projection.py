"""Projection tests — seeded determinism, arithmetic-exact zero-return cases,
goal-probability monotonicity, and withdrawal success/failure edges."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core import projection
from core.projection import (
    PERCENTILES,
    PROJECTION_CAVEAT,
    ProjectionResult,
    WithdrawalResult,
    project_monte_carlo,
    simulate_withdrawals,
)


def _returns(values, start="2015-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


def _sample_returns(n=500, seed=0):
    # A plausible daily-return series (mildly positive drift, realistic vol).
    rng = np.random.default_rng(seed)
    return _returns(rng.normal(0.0004, 0.01, size=n))


# --- Monte Carlo: determinism ----------------------------------------------------

def test_monte_carlo_seed_reproducible():
    rets = _sample_returns()
    kw = dict(years=3, n_paths=200, start_value=10_000.0, monthly_contribution=100.0, seed=7)
    a = project_monte_carlo(rets, **kw)
    b = project_monte_carlo(rets, **kw)
    pd.testing.assert_frame_equal(a.bands, b.bands)
    pd.testing.assert_series_equal(a.contributed, b.contributed)
    assert a.terminal_percentiles == b.terminal_percentiles
    np.testing.assert_array_equal(a.terminal_values, b.terminal_values)


def test_monte_carlo_different_seed_differs():
    rets = _sample_returns()
    kw = dict(years=3, n_paths=200, start_value=10_000.0, monthly_contribution=100.0)
    a = project_monte_carlo(rets, seed=1, **kw)
    b = project_monte_carlo(rets, seed=2, **kw)
    assert not np.array_equal(a.terminal_values, b.terminal_values)


# --- Monte Carlo: zero-return arithmetic exactness -------------------------------

def test_monte_carlo_zero_returns_exact_bands():
    rets = _returns([0.0] * 300)
    years, contrib = 2, 100.0
    res = project_monte_carlo(
        rets, years=years, n_paths=50, start_value=1_000.0,
        monthly_contribution=contrib, seed=3,
    )
    n_months = years * 12
    # Every path is identical: value at month m = start + m*contrib.
    for m in range(n_months + 1):
        expected = 1_000.0 + m * contrib
        for col in res.bands.columns:
            assert res.bands.iloc[m][col] == pytest.approx(expected)
    # Terminal & contributed line up.
    assert res.terminal_percentiles["p50"] == pytest.approx(1_000.0 + n_months * contrib)
    assert res.contributed.iloc[-1] == pytest.approx(1_000.0 + n_months * contrib)
    assert res.contributed.iloc[0] == pytest.approx(1_000.0)


def test_monte_carlo_zero_returns_no_contrib_is_flat():
    rets = _returns([0.0] * 300)
    res = project_monte_carlo(rets, years=2, n_paths=10, start_value=5_000.0, seed=1)
    assert (res.bands.to_numpy() == 5_000.0).all()


# --- Monte Carlo: escalation -----------------------------------------------------

def test_monte_carlo_escalation_raises_contributed():
    rets = _returns([0.0] * 300)
    flat = project_monte_carlo(
        rets, years=2, n_paths=5, start_value=0.0, monthly_contribution=100.0, seed=1,
    )
    esc = project_monte_carlo(
        rets, years=2, n_paths=5, start_value=0.0, monthly_contribution=100.0,
        escalation_pct=10.0, seed=1,
    )
    # Year 1: 12 * 100 = 1200 for both. Year 2: escalated pays 110/mo.
    assert flat.contributed.iloc[12] == pytest.approx(1200.0)
    assert esc.contributed.iloc[12] == pytest.approx(1200.0)
    assert esc.contributed.iloc[-1] == pytest.approx(1200.0 + 12 * 110.0)
    assert flat.contributed.iloc[-1] == pytest.approx(2400.0)


# --- Monte Carlo: goal_probability ----------------------------------------------

def test_goal_probability_bounds_and_monotonic():
    rets = _sample_returns()
    res = project_monte_carlo(
        rets, years=4, n_paths=500, start_value=10_000.0,
        monthly_contribution=200.0, seed=11,
    )
    assert res.goal_probability(0.0) == 1.0
    assert res.goal_probability(1e15) == 0.0
    goals = np.linspace(0, res.terminal_values.max(), 20)
    probs = [res.goal_probability(g) for g in goals]
    # Monotonically non-increasing in the goal.
    assert all(probs[i] >= probs[i + 1] - 1e-12 for i in range(len(probs) - 1))


def test_percentile_ordering_monte_carlo():
    rets = _sample_returns()
    res = project_monte_carlo(
        rets, years=3, n_paths=300, start_value=10_000.0,
        monthly_contribution=100.0, seed=5,
    )
    cols = [f"p{p}" for p in PERCENTILES]
    b = res.bands[cols].to_numpy()
    assert np.all(np.diff(b, axis=1) >= -1e-9)  # p5<=p25<=p50<=p75<=p95 each month


def test_projection_result_type_and_caveat():
    rets = _sample_returns()
    res = project_monte_carlo(rets, years=1, n_paths=10, start_value=1_000.0)
    assert isinstance(res, ProjectionResult)
    assert res.caveat == PROJECTION_CAVEAT
    assert "not financial advice" in PROJECTION_CAVEAT.lower()
    # months = years*12 rows + the starting month 0.
    assert len(res.bands) == 1 * 12 + 1


# --- Withdrawals -----------------------------------------------------------------

def test_withdrawals_seed_reproducible():
    rets = _sample_returns()
    kw = dict(start_balance=1_000_000.0, years=10, withdrawal=2_000.0, n_paths=200, seed=9)
    a = simulate_withdrawals(rets, **kw)
    b = simulate_withdrawals(rets, **kw)
    assert a.success_rate == b.success_rate
    pd.testing.assert_frame_equal(a.bands, b.bands)
    np.testing.assert_array_equal(a.years_lasted, b.years_lasted)


def test_withdrawals_generous_balance_tiny_withdrawal_always_succeeds():
    rets = _returns([0.0] * 300)  # zero returns -> pure drawdown, worst case for growth
    res = simulate_withdrawals(
        rets, start_balance=1_000_000.0, years=5, withdrawal=100.0,
        inflation_pct=0.0, n_paths=100, seed=1,
    )
    assert res.success_rate == 1.0
    # Never depleted -> every path lasts the full horizon.
    assert (res.years_lasted == 5).all()


def test_withdrawals_tiny_balance_huge_withdrawal_always_fails():
    rets = _sample_returns()
    res = simulate_withdrawals(
        rets, start_balance=100.0, years=10, withdrawal=1_000_000.0,
        n_paths=100, seed=1,
    )
    assert res.success_rate == 0.0
    # Depleted on the very first month -> zero years lasted, < horizon.
    assert (res.years_lasted < 10).all()
    assert res.years_lasted.max() == pytest.approx(0.0)


def test_withdrawals_percentile_ordering():
    rets = _sample_returns()
    res = simulate_withdrawals(
        rets, start_balance=500_000.0, years=8, withdrawal=2_500.0,
        n_paths=300, seed=4,
    )
    cols = [f"p{p}" for p in PERCENTILES]
    b = res.bands[cols].to_numpy()
    assert np.all(np.diff(b, axis=1) >= -1e-9)
    # years-lasted percentiles are ordered too.
    yl = [res.years_lasted_percentiles[c] for c in cols]
    assert all(yl[i] <= yl[i + 1] + 1e-12 for i in range(len(yl) - 1))


def test_withdrawals_rate_mode_runs_and_is_reasonable():
    rets = _sample_returns()
    res = simulate_withdrawals(
        rets, start_balance=1_000_000.0, years=30, withdrawal=4.0,
        withdrawal_is_rate=True, n_paths=300, seed=8,
    )
    assert isinstance(res, WithdrawalResult)
    assert 0.0 <= res.success_rate <= 1.0
    assert res.caveat == PROJECTION_CAVEAT


def test_withdrawals_result_type_and_caveat():
    rets = _sample_returns()
    res = simulate_withdrawals(
        rets, start_balance=100_000.0, years=2, withdrawal=500.0, n_paths=10,
    )
    assert isinstance(res, WithdrawalResult)
    assert len(res.bands) == 2 * 12 + 1


# --- input validation ------------------------------------------------------------

def test_empty_returns_raises():
    empty = pd.Series([np.nan, np.nan])
    with pytest.raises(ValueError, match="empty"):
        project_monte_carlo(empty, years=1, n_paths=5, start_value=1_000.0)


def test_module_exposes_caveat_constant():
    assert isinstance(projection.PROJECTION_CAVEAT, str)
    assert len(projection.PROJECTION_CAVEAT) > 0


def test_bootstrap_survives_total_loss_datapoint():
    # A bad-data row of -100% must not poison the bands with NaN (clipped just above -1).
    rets = _sample_returns().copy()
    rets.iloc[50] = -1.0
    res = project_monte_carlo(rets, years=1, n_paths=20, start_value=1_000.0, seed=7)
    assert np.isfinite(res.bands.to_numpy()).all()
