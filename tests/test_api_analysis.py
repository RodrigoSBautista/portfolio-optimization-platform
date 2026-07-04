"""API simulate + optimize tests — offline via the fake price provider."""

from __future__ import annotations

import pytest

from tests.api_helpers import auth_headers, build_client


@pytest.fixture
def client():
    client, teardown = build_client()
    yield client
    teardown()


def test_simulate_returns_series_and_metrics(client):
    headers = auth_headers(client, "sim")
    body = {
        "spec": {
            "name": "Sim",
            "benchmark_symbol": "SPY",
            "holdings": [
                {"symbol": "AAPL", "weight": 0.5},
                {"symbol": "MSFT", "weight": 0.5},
            ],
            "contributions": [{"kind": "lump_sum", "amount": 1000.0}],
        },
        "start": "2021-01-04",
        "benchmark": "SPY",
    }
    resp = client.post("/api/simulate", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["series"], "expected a non-empty series"
    point = data["series"][0]
    assert {"date", "value", "invested", "benchmark"} <= set(point)
    assert data["invested"] == pytest.approx(1000.0)
    assert "Sim" in data["metrics"]
    assert "SPY" in data["metrics"]  # benchmark column present
    assert data["benchmark"] == "SPY"


def test_simulate_requires_auth(client):
    body = {"spec": {"name": "x", "holdings": [{"symbol": "AAPL", "weight": 1.0}]},
            "start": "2021-01-04"}
    assert client.post("/api/simulate", json=body).status_code == 401


def test_simulate_no_holdings_is_400(client):
    headers = auth_headers(client, "empty")
    body = {"spec": {"name": "x", "holdings": []}, "start": "2021-01-04"}
    assert client.post("/api/simulate", json=body, headers=headers).status_code == 400


def test_optimize_allocate(client):
    headers = auth_headers(client, "opt")
    body = {
        "mode": "allocate",
        "method": "Inverse-volatility",
        "tickers": ["AAPL", "MSFT", "GOOG", "AMZN"],
        "lookback_years": 1,
        "benchmark": "SPY",
    }
    resp = client.post("/api/optimize", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert pytest.approx(sum(data["suggested"].values()), abs=1e-6) == 1.0
    assert pytest.approx(sum(data["baseline"].values()), abs=1e-6) == 1.0
    assert data["comparison_series"]
    cp = data["comparison_series"][0]
    assert {"date", "suggested", "equal_weight", "benchmark"} <= set(cp)
    assert "Equal weight" in data["metrics"]
    assert "SPY" in data["metrics"]
    # VALUE assertions (regression: specs once carried no cash -> flat $0 series and
    # all-zero metrics). The growth comparison must start at the nominal lump sum and
    # actually move over the window.
    assert cp["suggested"] == pytest.approx(10_000.0)
    assert cp["equal_weight"] == pytest.approx(10_000.0)
    last = data["comparison_series"][-1]
    assert last["suggested"] > 0 and last["suggested"] != pytest.approx(10_000.0)
    assert data["metrics"]["Equal weight"]["Total return"] != "0.0%"


def test_optimize_select_then_allocate(client):
    headers = auth_headers(client, "optsel")
    body = {
        "mode": "select",
        "method": "Inverse-volatility",  # allocation method
        "candidates": ["AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "META"],
        "k": 3,
        "selection_method": "Low volatility",  # selection method
        "lookback_years": 1,
        "benchmark": "SPY",
    }
    resp = client.post("/api/optimize", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["selected"]) == 3
    assert pytest.approx(sum(data["suggested"].values()), abs=1e-6) == 1.0
    assert pytest.approx(sum(data["baseline"].values()), abs=1e-6) == 1.0


def test_optimize_unknown_method_is_400(client):
    headers = auth_headers(client, "optbad")
    body = {
        "mode": "allocate",
        "method": "Definitely Not A Method",
        "tickers": ["AAPL", "MSFT"],
        "lookback_years": 1,
    }
    assert client.post("/api/optimize", json=body, headers=headers).status_code == 400
