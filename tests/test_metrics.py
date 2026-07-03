"""Metric tests — hand-verified against closed-form values."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core import metrics


def _index(values, start="2020-01-01", periods=None):
    periods = periods or len(values)
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


def test_total_return():
    assert metrics.total_return(_index([100, 110])) == pytest.approx(0.10)


def test_cagr_one_year_doubling():
    # ~1 year apart (366 days, leap year), value doubles -> ~100% CAGR.
    s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2020-01-01", "2021-01-01"]))
    assert metrics.cagr(s) == pytest.approx(1.0, abs=0.01)


def test_annualized_volatility_matches_manual():
    rets = pd.Series([0.01, -0.01, 0.02, -0.02])
    expected = rets.std(ddof=1) * np.sqrt(252)
    assert metrics.annualized_volatility(rets) == expected


def test_sharpe_zero_when_flat():
    rets = pd.Series([0.0, 0.0, 0.0])
    # Flat returns -> zero std -> NaN regardless of rf.
    assert np.isnan(metrics.sharpe_ratio(rets, risk_free_rate=0.0))


def test_sharpe_positive_for_steady_gains():
    # Pin rf=0 so the historical assertion holds; gains far exceed the daily rf.
    rets = pd.Series([0.01, 0.011, 0.009, 0.0105])
    assert metrics.sharpe_ratio(rets, risk_free_rate=0.0) > 0


def test_sharpe_default_risk_free_rate_is_four_percent():
    assert metrics.DEFAULT_RISK_FREE_RATE == 0.04
    rets = pd.Series([0.01, -0.01, 0.02, -0.02])
    # Hand-computed excess-return Sharpe with rf=4%/yr.
    std = rets.std(ddof=1)
    excess = rets - 0.04 / 252
    expected = excess.mean() / std * np.sqrt(252)
    assert metrics.sharpe_ratio(rets) == pytest.approx(expected)
    # Non-zero rf lowers Sharpe vs rf=0.
    assert metrics.sharpe_ratio(rets) < metrics.sharpe_ratio(rets, risk_free_rate=0.0)


def test_sortino_hand_computed():
    rets = pd.Series([0.02, -0.01, 0.03, -0.02])
    # Downside deviation = RMS of the negatives {-0.01, -0.02}.
    downside_dev = np.sqrt(np.mean(np.square(np.array([-0.01, -0.02]))))
    excess = rets - 0.04 / 252
    expected = excess.mean() / downside_dev * np.sqrt(252)
    assert metrics.sortino_ratio(rets) == pytest.approx(expected)


def test_sortino_nan_when_no_downside():
    rets = pd.Series([0.01, 0.02, 0.03])
    assert np.isnan(metrics.sortino_ratio(rets))


def test_sortino_exceeds_sharpe_when_downside_below_total_vol():
    # A series with modest downside vs larger upside -> Sortino > Sharpe.
    rets = pd.Series([0.05, -0.01, 0.04, -0.01, 0.06])
    assert metrics.sortino_ratio(rets, risk_free_rate=0.0) > metrics.sharpe_ratio(
        rets, risk_free_rate=0.0
    )


def test_calmar_hand_computed():
    # Index doubles over exactly one leap year (366 days) -> CAGR ~= 1.0;
    # peak 2.0 then trough 1.5 -> drawdown of -25%.
    idx = pd.to_datetime(["2020-01-01", "2020-07-01", "2021-01-01"])
    s = pd.Series([1.0, 2.0, 1.5], index=idx)
    ann = metrics.cagr(s)
    mdd = metrics.max_drawdown(s)  # 1.5/2.0 - 1 = -0.25
    assert mdd == pytest.approx(-0.25)
    assert metrics.calmar_ratio(s) == pytest.approx(ann / 0.25)


def test_calmar_nan_when_no_drawdown():
    s = _index([100, 101, 102, 103])  # monotonic -> zero drawdown
    assert np.isnan(metrics.calmar_ratio(s))


def test_calendar_year_returns_and_best_worst():
    # Two full calendar years: 2020 close 110 (from 100 base) = +10%; 2021 close 99
    # from prior close 110 = -10%.
    idx = pd.to_datetime(["2020-01-01", "2020-12-31", "2021-12-31"])
    s = pd.Series([100.0, 110.0, 99.0], index=idx)
    yr = metrics.calendar_year_returns(s)
    assert yr.loc[2020] == pytest.approx(0.10)
    assert yr.loc[2021] == pytest.approx(-0.10)
    assert metrics.best_year(s) == pytest.approx(0.10)
    assert metrics.worst_year(s) == pytest.approx(-0.10)


def test_beta_alpha_hand_computed():
    # Portfolio moves exactly 2x the benchmark each day -> beta = 2, alpha = 0.
    bench = _index([100, 101, 102, 101, 103])
    rb = bench.pct_change().dropna()
    # Build a portfolio index whose daily returns are exactly 2 * benchmark returns.
    port_rets = 2.0 * rb
    port_vals = [100.0]
    for r in port_rets:
        port_vals.append(port_vals[-1] * (1 + r))
    port = pd.Series(port_vals, index=bench.index)
    stats = metrics.benchmark_stats(port, bench, risk_free_rate=0.0)
    assert stats["beta"] == pytest.approx(2.0, abs=1e-9)
    assert stats["alpha"] == pytest.approx(0.0, abs=1e-9)


def test_beta_alpha_nan_on_flat_benchmark():
    port = _index([100, 101, 102, 103])
    flat = _index([50, 50, 50, 50])  # zero variance -> beta undefined
    stats = metrics.benchmark_stats(port, flat)
    assert np.isnan(stats["beta"])
    assert np.isnan(stats["alpha"])


def test_deflate_known_arithmetic():
    # 10%/yr inflation, values sampled exactly 1 leap year apart.
    idx = pd.to_datetime(["2020-01-01", "2021-01-01"])
    s = pd.Series([100.0, 110.0], index=idx)
    real = metrics.deflate(s, annual_inflation_pct=10.0)
    # First point unchanged; second divided by 1.10^(366/365.25).
    years = (idx[1] - idx[0]).days / 365.25
    assert real.iloc[0] == pytest.approx(100.0)
    assert real.iloc[1] == pytest.approx(110.0 / (1.10 ** years))


def test_deflate_zero_inflation_is_identity():
    s = _index([100, 110, 120])
    pd.testing.assert_series_equal(metrics.deflate(s, 0.0), s.astype(float))


def test_max_drawdown():
    # Peak 120 then trough 90 -> -25%.
    s = _index([100, 120, 90, 110])
    assert metrics.max_drawdown(s) == (90 / 120 - 1.0)


def test_return_index_starts_at_one():
    s = _index([50, 55, 60])
    ri = metrics.return_index(s)
    assert ri.iloc[0] == 1.0
    assert ri.iloc[-1] == 60 / 50


def test_summarize_keys():
    s = _index([100, 101, 102, 103])
    out = metrics.summarize(s)
    # Existing keys preserved; new metrics added (backward-compatible superset).
    assert {"total_return", "cagr", "volatility", "sharpe", "max_drawdown"} <= set(out)
    assert {"sortino", "calmar", "best_year", "worst_year"} <= set(out)
    # No benchmark supplied -> no beta/alpha keys.
    assert "beta" not in out
    assert "alpha" not in out


def test_summarize_uses_default_risk_free_rate():
    s = _index([100, 101, 100, 102, 101, 103])
    rets = metrics.daily_returns(s)
    out = metrics.summarize(s)
    assert out["sharpe"] == pytest.approx(metrics.sharpe_ratio(rets, 0.04))


def test_summarize_with_benchmark_adds_beta_alpha():
    port = _index([100, 102, 101, 104, 103, 106])
    bench = _index([100, 101, 100.5, 102, 101.5, 103])
    out = metrics.summarize(port, benchmark_index=bench)
    assert "beta" in out
    assert "alpha" in out
