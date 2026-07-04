"""API analytics tests — offline via the fake price provider.

Covers the extended ``/simulate`` (unit mapping, back-compat, real values, drawdown +
rolling) and the four new endpoints (``/project``, ``/retirement``, ``/frontier``,
``/diversification``): determinism, bounds, shapes, invariants, and the auth guards.
"""

from __future__ import annotations

import pytest

from tests.api_helpers import auth_headers, build_client


@pytest.fixture
def client():
    client, teardown = build_client()
    yield client
    teardown()


def _spec(holdings=None, contributions=None) -> dict:
    if holdings is None:
        holdings = [{"symbol": "AAPL", "weight": 0.5}, {"symbol": "MSFT", "weight": 0.5}]
    if contributions is None:
        contributions = [{"kind": "lump_sum", "amount": 1000.0}]
    return {
        "name": "Analytics",
        "benchmark_symbol": "SPY",
        "base_currency": "USD",
        "holdings": holdings,
        "contributions": contributions,
    }


def _sharpe(metrics: dict) -> float:
    return float(metrics["Analytics"]["Sharpe"].replace(",", ""))


# --- extended /simulate ---------------------------------------------------------


def test_simulate_risk_free_rate_mapping_lowers_sharpe(client):
    """rf is a FRACTION: a higher rf (0.04) must lower Sharpe vs rf=0.0."""
    headers = auth_headers(client, "rf")
    base = {"spec": _spec(), "start": "2021-01-04", "benchmark": "SPY"}

    low = client.post("/api/simulate", json={**base, "risk_free_rate": 0.0}, headers=headers)
    high = client.post("/api/simulate", json={**base, "risk_free_rate": 0.04}, headers=headers)
    assert low.status_code == 200 and high.status_code == 200
    assert _sharpe(low.json()["metrics"]) > _sharpe(high.json()["metrics"])


def test_simulate_backcompat_default_request(client):
    """A defaults-only request keeps existing keys and leaves new fields null."""
    headers = auth_headers(client, "bc")
    body = {"spec": _spec(), "start": "2021-01-04", "benchmark": "SPY"}
    resp = client.post("/api/simulate", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Existing top-level keys + values behave as before.
    assert {"series", "metrics", "final_value", "invested", "gain_pct", "dropped",
            "benchmark"} <= set(data)
    assert data["invested"] == pytest.approx(1000.0)
    assert data["benchmark"] == "SPY"
    # Original five metric rows unchanged (still present).
    assert {"Total return", "CAGR", "Volatility (ann.)", "Sharpe",
            "Max drawdown"} <= set(data["metrics"]["Analytics"])
    # New fields present but empty (no behavior added when defaults).
    assert data["real_final_value"] is None
    assert data["drawdown"] is None
    assert data["rolling"] is None
    assert data["series"][0]["real_value"] is None
    # No benchmark-vs-itself beta on the SPY column.
    assert "Beta" not in data["metrics"]["SPY"]
    # Portfolio gains beta/alpha (benchmark present) + the new risk-adjusted rows.
    assert {"Sortino", "Calmar", "Best year", "Worst year", "Beta",
            "Alpha (ann.)"} <= set(data["metrics"]["Analytics"])


def test_simulate_inflation_deflates_final_value(client):
    """inflation_pct is a PERCENT: real final value is a touch below nominal."""
    headers = auth_headers(client, "infl")
    body = {"spec": _spec(), "start": "2021-01-04", "inflation_pct": 2.5}
    resp = client.post("/api/simulate", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["real_final_value"] is not None
    assert data["real_final_value"] < data["final_value"]
    # ~1yr window at 2.5%/yr => a few percent, NOT a 250% (fraction-vs-percent) blowup.
    assert data["real_final_value"] > data["final_value"] * 0.9
    assert data["series"][-1]["real_value"] is not None
    assert data["series"][0]["real_value"] == pytest.approx(data["series"][0]["value"])


def test_simulate_include_analytics_shapes(client):
    headers = auth_headers(client, "an")
    body = {"spec": _spec(), "start": "2021-01-04", "include_analytics": True}
    resp = client.post("/api/simulate", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["drawdown"] and {"date", "pct"} == set(data["drawdown"][0])
    assert all(p["pct"] <= 1e-9 for p in data["drawdown"])  # drawdown is <= 0

    assert data["rolling"] and {"date", "ret_1y", "vol_1y"} == set(data["rolling"][0])
    # None until the 252-day window fills, then populated near the end.
    assert data["rolling"][0]["ret_1y"] is None
    assert any(p["ret_1y"] is not None for p in data["rolling"])


def test_simulate_bad_rebalance_is_422(client):
    headers = auth_headers(client, "reb")
    body = {"spec": _spec(), "start": "2021-01-04", "rebalance": "fortnightly"}
    assert client.post("/api/simulate", json=body, headers=headers).status_code == 422


# --- /project -------------------------------------------------------------------


def test_project_deterministic_and_goal_bounds(client):
    headers = auth_headers(client, "proj")
    body = {"spec": _spec(), "years": 10, "n_paths": 500, "seed": 7,
            "start_value": 10000.0, "goal": 20000.0, "lookback_years": 5}
    a = client.post("/api/project", json=body, headers=headers)
    b = client.post("/api/project", json=body, headers=headers)
    assert a.status_code == 200 and b.status_code == 200, a.text
    da, db = a.json(), b.json()

    assert da == db  # fully deterministic for a fixed seed
    assert {"date", "p5", "p25", "p50", "p75", "p95"} == set(da["bands"][0])
    assert da["bands"][0]["date"].count("-") == 1  # "YYYY-MM"
    assert set(da["terminal"]) == {"p5", "p25", "p50", "p75", "p95"}
    # contributed includes the starting balance at month 0.
    assert da["contributed"][0]["value"] == pytest.approx(10000.0)
    assert 0.0 <= da["goal_probability"] <= 1.0
    assert da["caveat"]


def test_project_no_goal_is_null(client):
    headers = auth_headers(client, "proj_ng")
    body = {"spec": _spec(), "years": 5, "n_paths": 200, "start_value": 5000.0}
    resp = client.post("/api/project", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["goal_probability"] is None


def test_project_validation_422s(client):
    headers = auth_headers(client, "proj_bad")
    good = {"spec": _spec(), "years": 5, "start_value": 1000.0}
    assert client.post("/api/simulate", json={"spec": _spec(), "start": "2021-01-04"},
                       headers=headers).status_code == 200  # sanity
    # years out of range
    assert client.post("/api/project", json={**good, "years": 0},
                       headers=headers).status_code == 422
    assert client.post("/api/project", json={**good, "years": 99},
                       headers=headers).status_code == 422
    # n_paths above the cap
    assert client.post("/api/project", json={**good, "n_paths": 9000},
                       headers=headers).status_code == 422
    # non-positive start_value
    assert client.post("/api/project", json={**good, "start_value": 0},
                       headers=headers).status_code == 422
    # no holdings -> no returns
    empty = {"spec": _spec(holdings=[]), "years": 5, "start_value": 1000.0}
    assert client.post("/api/project", json=empty, headers=headers).status_code == 422


# --- /retirement ----------------------------------------------------------------


def test_retirement_success_extremes(client):
    headers = auth_headers(client, "ret")
    spec = _spec()
    generous = {"spec": spec, "start_balance": 1_000_000.0, "years": 10,
                "withdrawal": {"kind": "fixed", "amount": 10.0}, "n_paths": 300}
    absurd = {"spec": spec, "start_balance": 1000.0, "years": 10,
              "withdrawal": {"kind": "fixed", "amount": 100000.0}, "n_paths": 300}

    g = client.post("/api/retirement", json=generous, headers=headers)
    a = client.post("/api/retirement", json=absurd, headers=headers)
    assert g.status_code == 200 and a.status_code == 200, g.text
    assert g.json()["success_rate"] == pytest.approx(1.0)
    assert a.json()["success_rate"] < 1.0
    assert set(g.json()["years_lasted"]) == {"p5", "p25", "p50", "p75", "p95"}
    assert {"date", "p5", "p25", "p50", "p75", "p95"} == set(g.json()["bands"][0])


def test_retirement_rate_kind(client):
    headers = auth_headers(client, "ret_rate")
    # `rate` is an annual FRACTION on the wire (0.04 = the 4% rule).
    body = {"spec": _spec(), "start_balance": 500000.0, "years": 20,
            "withdrawal": {"kind": "rate", "rate": 0.04}, "n_paths": 300}
    resp = client.post("/api/retirement", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    assert 0.0 <= resp.json()["success_rate"] <= 1.0


def test_retirement_rate_unit_is_fraction_not_percent(client):
    """Pins the fraction->percent conversion at the API boundary (a 100x seam).

    A 95%/yr withdrawal (rate=0.95) is unsustainable on any realistic return path,
    so success must collapse to ~0; if the fraction were mis-read as 0.95 PERCENT,
    success would be ~1.0. The converse leg (0.1%/yr) must succeed.
    """
    headers = auth_headers(client, "ret_units")
    base = {"spec": _spec(), "start_balance": 100000.0, "years": 10,
            "n_paths": 200, "seed": 7}

    ruinous = client.post("/api/retirement", json={
        **base, "withdrawal": {"kind": "rate", "rate": 0.95}}, headers=headers)
    assert ruinous.status_code == 200, ruinous.text
    body = ruinous.json()
    assert body["success_rate"] < 0.05
    assert body["years_lasted"]["p95"] < 10

    trivial = client.post("/api/retirement", json={
        **base, "withdrawal": {"kind": "rate", "rate": 0.001}}, headers=headers)
    assert trivial.status_code == 200
    assert trivial.json()["success_rate"] == 1.0


def test_retirement_bad_withdrawal_is_422(client):
    headers = auth_headers(client, "ret_bad")
    spec = _spec()
    # fixed without amount
    assert client.post("/api/retirement", json={
        "spec": spec, "start_balance": 1000.0, "years": 5,
        "withdrawal": {"kind": "fixed"}}, headers=headers).status_code == 422
    # rate without rate
    assert client.post("/api/retirement", json={
        "spec": spec, "start_balance": 1000.0, "years": 5,
        "withdrawal": {"kind": "rate"}}, headers=headers).status_code == 422
    # unknown kind
    assert client.post("/api/retirement", json={
        "spec": spec, "start_balance": 1000.0, "years": 5,
        "withdrawal": {"kind": "monthly", "amount": 10.0}}, headers=headers).status_code == 422


# --- /frontier ------------------------------------------------------------------


def test_frontier_shapes_and_pareto(client):
    headers = auth_headers(client, "front")
    body = {"tickers": ["AAPL", "MSFT", "GOOG", "AMZN"], "lookback_years": 3,
            "n_samples": 800, "seed": 3,
            "extra_points": [{"label": "My mix", "weights": {"AAPL": 1.0, "MSFT": 1.0}}]}
    resp = client.post("/api/frontier", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["cloud"] and {"vol", "ret"} == set(data["cloud"][0])
    assert len(data["cloud"]) <= 800
    labels = {m["label"] for m in data["markers"]}
    assert "Equal weight" in labels and "My mix" in labels

    # Pareto frontier: return is non-decreasing as vol increases.
    rets = [p["ret"] for p in data["frontier"]]
    assert rets == sorted(rets)
    vols = [p["vol"] for p in data["frontier"]]
    assert vols == sorted(vols)


def test_frontier_too_few_tickers_is_422(client):
    headers = auth_headers(client, "front_few")
    body = {"tickers": ["AAPL"], "lookback_years": 3}
    assert client.post("/api/frontier", json=body, headers=headers).status_code == 422


# --- /diversification -----------------------------------------------------------


def test_diversification_matrix_and_risk(client):
    headers = auth_headers(client, "div")
    body = {"tickers": ["AAPL", "MSFT", "GOOG", "AMZN"], "lookback_years": 3}
    resp = client.post("/api/diversification", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    m = data["matrix"]
    n = len(m["tickers"])
    assert len(m["values"]) == n and all(len(row) == n for row in m["values"])
    for i in range(n):
        assert m["values"][i][i] == pytest.approx(1.0)
        for j in range(n):
            assert m["values"][i][j] == pytest.approx(m["values"][j][i])  # symmetric

    assert data["clusters"] and {"label", "members"} == set(data["clusters"][0])
    pcts = [c["pct"] for c in data["risk_contributions"]]
    # Fractions summing to ~1.0 (NOT percentages summing to 100).
    assert sum(pcts) == pytest.approx(1.0, abs=1e-4)
    assert all(0.0 <= p <= 1.0 for p in pcts)
    assert pcts == sorted(pcts, reverse=True)  # sorted descending


def test_diversification_weighted_risk(client):
    headers = auth_headers(client, "div_w")
    body = {"tickers": ["AAPL", "MSFT", "GOOG"], "lookback_years": 3,
            "weights": {"AAPL": 0.6, "MSFT": 0.3, "GOOG": 0.1}}
    resp = client.post("/api/diversification", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    pcts = [c["pct"] for c in resp.json()["risk_contributions"]]
    assert sum(pcts) == pytest.approx(1.0, abs=1e-4)  # fractions summing to ~1.0


# --- unit sanity: all numeric analytics fields are FRACTIONS --------------------


def test_analytics_response_fields_are_fractions(client):
    """Response numerics are fractions, not percents (the React charts x100 for display)."""
    headers = auth_headers(client, "units")

    # Drawdown values in [-1, 0]; rolling stats are fractions (|value| < 3 as a sanity).
    sim = client.post("/api/simulate", json={
        "spec": _spec(), "start": "2021-01-04", "include_analytics": True}, headers=headers)
    assert sim.status_code == 200, sim.text
    sd = sim.json()
    assert all(-1.0 <= p["pct"] <= 0.0 for p in sd["drawdown"])
    for p in sd["rolling"]:
        for key in ("ret_1y", "vol_1y"):
            if p[key] is not None:
                assert abs(p[key]) < 3.0  # a fraction, not a *100 percentage

    # Frontier vol/ret are fractions (annualized) -> small magnitudes.
    fr = client.post("/api/frontier", json={
        "tickers": ["AAPL", "MSFT", "GOOG"], "n_samples": 300, "seed": 1}, headers=headers)
    assert fr.status_code == 200, fr.text
    for p in fr.json()["cloud"]:
        assert abs(p["ret"]) < 5.0 and 0.0 <= p["vol"] < 5.0

    # Risk contributions are fractions summing to ~1.0.
    dv = client.post("/api/diversification", json={
        "tickers": ["AAPL", "MSFT", "GOOG"]}, headers=headers)
    assert dv.status_code == 200, dv.text
    assert sum(c["pct"] for c in dv.json()["risk_contributions"]) == pytest.approx(1.0, abs=1e-4)


# --- auth guards ----------------------------------------------------------------


def test_all_endpoints_require_auth(client):
    assert client.post("/api/simulate", json={
        "spec": _spec(), "start": "2021-01-04"}).status_code == 401
    assert client.post("/api/project", json={
        "spec": _spec(), "years": 5, "start_value": 1000.0}).status_code == 401
    assert client.post("/api/retirement", json={
        "spec": _spec(), "start_balance": 1000.0, "years": 5,
        "withdrawal": {"kind": "fixed", "amount": 10.0}}).status_code == 401
    assert client.post("/api/frontier", json={
        "tickers": ["AAPL", "MSFT"]}).status_code == 401
    assert client.post("/api/diversification", json={
        "tickers": ["AAPL", "MSFT"]}).status_code == 401
