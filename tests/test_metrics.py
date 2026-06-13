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
    assert np.isnan(metrics.sharpe_ratio(rets))


def test_sharpe_positive_for_steady_gains():
    rets = pd.Series([0.01, 0.011, 0.009, 0.0105])
    assert metrics.sharpe_ratio(rets) > 0


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
    assert set(out) == {"total_return", "cagr", "volatility", "sharpe", "max_drawdown"}
