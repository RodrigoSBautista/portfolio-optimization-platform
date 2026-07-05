"""API compare + tracking tests — offline via a fake price provider.

Covers the compare response shape, the fairness/shared-window invariant (portfolios
with different-length ticker histories share ONE window, so equal recurring flows yield
equal ``invested``), per-user 404 isolation, valuations shape, refresh idempotency, and
the 401/422 guards.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api import deps
from api.main import app
from data.prices import PriceService
from storage.db import make_session_factory
from storage.models import Base
from tests.api_helpers import auth_headers, build_client


class StaggeredProvider:
    """Fake prices where some tickers start later than others.

    ``LATE`` tickers begin ``late_offset`` business days after ``start`` and have a
    shorter history. ``common_history`` must clip every portfolio + benchmark to the
    latest common start, so the shared window is identical regardless of which
    portfolio is simulated — the core fairness invariant.
    """

    LATE = {"LATE"}
    LATE_OFFSET = 40
    # ``MISSING`` tickers return no column at all — the delisted/invalid case
    # (yfinance yields nothing), which PriceService silently omits.
    MISSING = {"DELISTED"}

    def fetch_adjusted_close(
        self, tickers: list[str], start: date, end: date | None = None
    ) -> pd.DataFrame:
        full = pd.date_range(start=pd.Timestamp(start), periods=260, freq="B")
        data: dict[str, pd.Series] = {}
        for t in tickers:
            sym = t.upper()
            if sym in self.MISSING:
                continue
            seed = sum(ord(c) for c in sym)
            rng = np.random.default_rng(seed)
            drift = 0.0002 + (seed % 7) * 0.00005
            shocks = rng.normal(drift, 0.01, size=len(full))
            prices = 100.0 * np.exp(np.cumsum(shocks))
            series = pd.Series(prices, index=full)
            if sym in self.LATE:
                series = series.iloc[self.LATE_OFFSET :]
            data[sym] = series
        return pd.DataFrame(data)


def build_client_with(provider) -> tuple:
    """Like ``api_helpers.build_client`` but with a caller-supplied price provider."""
    from fastapi.testclient import TestClient

    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)

    app.dependency_overrides[deps.get_session_factory] = lambda: factory
    app.dependency_overrides[deps.get_price_service] = lambda: PriceService(provider=provider)

    client = TestClient(app)

    def teardown():
        app.dependency_overrides.clear()
        engine.dispose()

    return client, teardown


@pytest.fixture
def client():
    client, teardown = build_client()
    yield client
    teardown()


def _make_portfolio(client, headers, name: str, holdings: list[dict]) -> int:
    """Create a portfolio with a monthly recurring flow so invested tracks the window."""
    spec = {
        "name": name,
        "benchmark_symbol": "SPY",
        "base_currency": "USD",
        "holdings": holdings,
        "contributions": [
            {"kind": "lump_sum", "amount": 1000.0},
            {
                "kind": "recurring",
                "amount": 100.0,
                "frequency": "monthly",
                "start_date": "2021-01-04",
            },
        ],
    }
    resp = client.post("/api/portfolios", json=spec, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# --- compare --------------------------------------------------------------------


def test_compare_shape(client):
    headers = auth_headers(client, "cmp")
    a = _make_portfolio(client, headers, "Alpha", [{"symbol": "AAPL", "weight": 1.0}])
    b = _make_portfolio(client, headers, "Beta", [{"symbol": "MSFT", "weight": 1.0}])

    body = {"portfolio_ids": [a, b], "start": "2021-01-04", "benchmark": "SPY"}
    resp = client.post("/api/compare", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert len(data["results"]) == 2
    assert {r["id"] for r in data["results"]} == {a, b}
    first = data["results"][0]
    assert {"id", "name", "series", "final_value", "invested", "metrics"} <= set(first)
    assert first["series"], "expected a non-empty value series"
    assert {"date", "value"} == set(first["series"][0])
    assert "CAGR" in first["metrics"]
    # Benchmark computed once and shared.
    assert data["benchmark_series"]
    assert {"date", "value"} == set(data["benchmark_series"][0])
    assert data["benchmark_metrics"] and "CAGR" in data["benchmark_metrics"]


def test_compare_shared_window_equal_invested():
    """Two portfolios with different-length ticker histories share one window.

    ``LATE`` starts 40 business days after ``EARLY``; ``common_history`` clips both
    portfolios + the benchmark to the same later start, so equal recurring flows produce
    EQUAL ``invested`` and IDENTICAL series dates.
    """
    client, teardown = build_client_with(StaggeredProvider())
    try:
        headers = auth_headers(client, "fair")
        early = _make_portfolio(client, headers, "Early", [{"symbol": "EARLY", "weight": 1.0}])
        late = _make_portfolio(client, headers, "Late", [{"symbol": "LATE", "weight": 1.0}])

        body = {"portfolio_ids": [early, late], "start": "2021-01-04", "benchmark": "SPY"}
        resp = client.post("/api/compare", json=body, headers=headers)
        assert resp.status_code == 200, resp.text
        results = {r["name"]: r for r in resp.json()["results"]}

        assert results["Early"]["invested"] == pytest.approx(results["Late"]["invested"])
        early_dates = [p["date"] for p in results["Early"]["series"]]
        late_dates = [p["date"] for p in results["Late"]["series"]]
        assert early_dates == late_dates
    finally:
        teardown()


def test_compare_foreign_id_is_404(client):
    a_headers = auth_headers(client, "cmp_a")
    b_headers = auth_headers(client, "cmp_b")
    a1 = _make_portfolio(client, a_headers, "A1", [{"symbol": "AAPL", "weight": 1.0}])
    a2 = _make_portfolio(client, a_headers, "A2", [{"symbol": "MSFT", "weight": 1.0}])
    b1 = _make_portfolio(client, b_headers, "B1", [{"symbol": "GOOG", "weight": 1.0}])

    # B mixes their own id with one of A's -> 404 (never leaks A's data).
    body = {"portfolio_ids": [b1, a1], "start": "2021-01-04", "benchmark": "SPY"}
    assert client.post("/api/compare", json=body, headers=b_headers).status_code == 404
    # A comparing their own two is fine.
    ok = {"portfolio_ids": [a1, a2], "start": "2021-01-04", "benchmark": "SPY"}
    assert client.post("/api/compare", json=ok, headers=a_headers).status_code == 200


def test_compare_requires_two_to_three(client):
    headers = auth_headers(client, "cmp_count")
    a = _make_portfolio(client, headers, "One", [{"symbol": "AAPL", "weight": 1.0}])
    body = {"portfolio_ids": [a], "start": "2021-01-04", "benchmark": "SPY"}
    assert client.post("/api/compare", json=body, headers=headers).status_code == 422


def test_compare_requires_auth(client):
    body = {"portfolio_ids": [1, 2], "start": "2021-01-04", "benchmark": "SPY"}
    assert client.post("/api/compare", json=body).status_code == 401


# --- valuations + refresh -------------------------------------------------------


def test_valuations_shape_and_refresh_idempotent(client):
    headers = auth_headers(client, "track")
    pid = _make_portfolio(client, headers, "Tracked", [{"symbol": "AAPL", "weight": 1.0}])

    # Empty before any refresh.
    resp = client.get(f"/api/portfolios/{pid}/valuations", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["valuations"] == []

    first = client.post(
        f"/api/portfolios/{pid}/refresh", json={"start": "2021-01-04"}, headers=headers
    )
    assert first.status_code == 200, first.text
    written = first.json()["written"]
    assert written > 0

    resp = client.get(f"/api/portfolios/{pid}/valuations", headers=headers)
    assert resp.status_code == 200
    valuations = resp.json()["valuations"]
    assert len(valuations) == written
    point = valuations[0]
    assert {"date", "market_value", "benchmark_value"} == set(point)
    assert point["benchmark_value"] is not None

    # Re-run: idempotent upsert on (portfolio_id, as_of_date) -> same count, no dupes.
    second = client.post(
        f"/api/portfolios/{pid}/refresh", json={"start": "2021-01-04"}, headers=headers
    )
    assert second.status_code == 200
    assert second.json()["written"] == written

    resp = client.get(f"/api/portfolios/{pid}/valuations", headers=headers)
    rows = resp.json()["valuations"]
    assert len(rows) == written
    dates = [r["date"] for r in rows]
    assert len(dates) == len(set(dates)), "no duplicate valuation dates"


def test_refresh_defaults_start_when_omitted(client):
    headers = auth_headers(client, "track_default")
    pid = _make_portfolio(client, headers, "Defaulted", [{"symbol": "AAPL", "weight": 1.0}])
    # Omit start entirely -> defaults to Jan 1 three years ago; the fake provider yields a
    # full window from that default, so rows are actually written and persisted.
    resp = client.post(f"/api/portfolios/{pid}/refresh", json={}, headers=headers)
    assert resp.status_code == 200, resp.text
    written = resp.json()["written"]
    assert written > 0
    stored = client.get(f"/api/portfolios/{pid}/valuations", headers=headers).json()["valuations"]
    assert len(stored) == written


def test_compare_rejects_duplicate_ids(client):
    headers = auth_headers(client, "cmp_dupe")
    a = _make_portfolio(client, headers, "Dupe", [{"symbol": "AAPL", "weight": 1.0}])
    # [a, a] passes the 2-3 length check but is not a real comparison -> 422.
    body = {"portfolio_ids": [a, a], "start": "2021-01-04", "benchmark": "SPY"}
    assert client.post("/api/compare", json=body, headers=headers).status_code == 422


def test_refresh_survives_priceless_holding():
    """A saved 60/40 portfolio where one holding is delisted (no price data).

    ``available`` is non-empty (AAPL survives), so the pre-simulation guards don't fire.
    ``build_valuations`` must weight only the surviving ticker (regression: it used to
    pass the unfiltered spec weights and 500 on the missing column). The refresh succeeds
    and writes rows for AAPL alone.
    """
    client, teardown = build_client_with(StaggeredProvider())
    try:
        headers = auth_headers(client, "priceless")
        pid = _make_portfolio(
            client,
            headers,
            "Partly delisted",
            [{"symbol": "AAPL", "weight": 0.6}, {"symbol": "DELISTED", "weight": 0.4}],
        )
        resp = client.post(
            f"/api/portfolios/{pid}/refresh", json={"start": "2021-01-04"}, headers=headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["written"] > 0
        stored = client.get(
            f"/api/portfolios/{pid}/valuations", headers=headers
        ).json()["valuations"]
        assert len(stored) == resp.json()["written"]
        assert stored[0]["market_value"] > 0
    finally:
        teardown()


def test_compare_reports_dropped_holdings():
    """Comparing a portfolio with a delisted holding surfaces it in ``dropped``."""
    client, teardown = build_client_with(StaggeredProvider())
    try:
        headers = auth_headers(client, "cmp_dropped")
        a = _make_portfolio(
            client,
            headers,
            "HasDelisted",
            [{"symbol": "AAPL", "weight": 0.6}, {"symbol": "DELISTED", "weight": 0.4}],
        )
        b = _make_portfolio(client, headers, "Clean", [{"symbol": "MSFT", "weight": 1.0}])
        body = {"portfolio_ids": [a, b], "start": "2021-01-04", "benchmark": "SPY"}
        resp = client.post("/api/compare", json=body, headers=headers)
        assert resp.status_code == 200, resp.text
        results = {r["name"]: r for r in resp.json()["results"]}
        assert results["HasDelisted"]["dropped"] == ["DELISTED"]
        assert results["Clean"]["dropped"] == []
    finally:
        teardown()


# --- lot-based portfolios (smoke) -----------------------------------------------


def _make_lot_portfolio(client, headers, name: str, symbol: str) -> int:
    """Create a lot-based portfolio (dated purchases) and return its id."""
    spec = {
        "name": name,
        "benchmark_symbol": "SPY",
        "base_currency": "USD",
        "lots": [
            {"symbol": symbol, "date": "2021-01-04", "amount": 1000.0},
            {"symbol": symbol, "date": "2021-03-01", "amount": 500.0},
        ],
    }
    resp = client.post("/api/portfolios", json=spec, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # CRUD carries lots through create/get.
    assert len(body["lots"]) == 2
    assert body["holdings"] == []
    return body["id"]


def test_lot_portfolio_crud_round_trip(client):
    headers = auth_headers(client, "lotcrud")
    pid = _make_lot_portfolio(client, headers, "Lots", "AAPL")
    got = client.get(f"/api/portfolios/{pid}", headers=headers).json()
    assert {lot["symbol"] for lot in got["lots"]} == {"AAPL"}
    listed = client.get("/api/portfolios", headers=headers).json()
    assert listed[0]["lots"] and listed[0]["holdings"] == []


def test_compare_accepts_lot_specs(client):
    headers = auth_headers(client, "lotcmp")
    a = _make_lot_portfolio(client, headers, "LotsA", "AAPL")
    b = _make_lot_portfolio(client, headers, "LotsB", "MSFT")
    body = {"portfolio_ids": [a, b], "start": "2021-01-04", "benchmark": "SPY"}
    resp = client.post("/api/compare", json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["results"]) == 2
    assert all(r["series"] for r in data["results"])
    assert data["benchmark_series"]


def test_refresh_writes_valuations_for_lot_portfolio(client):
    headers = auth_headers(client, "lottrack")
    pid = _make_lot_portfolio(client, headers, "TrackedLots", "AAPL")
    resp = client.post(f"/api/portfolios/{pid}/refresh", json={}, headers=headers)
    assert resp.status_code == 200, resp.text
    written = resp.json()["written"]
    assert written > 0

    stored = client.get(f"/api/portfolios/{pid}/valuations", headers=headers).json()["valuations"]
    assert len(stored) == written
    assert stored[0]["market_value"] > 0
    assert stored[0]["benchmark_value"] is not None

    # Idempotent: re-running upserts in place, no duplicate dates.
    again = client.post(f"/api/portfolios/{pid}/refresh", json={}, headers=headers)
    assert again.json()["written"] == written
    rows = client.get(f"/api/portfolios/{pid}/valuations", headers=headers).json()["valuations"]
    dates = [r["date"] for r in rows]
    assert len(dates) == len(set(dates))


def test_valuations_foreign_id_is_404(client):
    a_headers = auth_headers(client, "val_a")
    b_headers = auth_headers(client, "val_b")
    a_pid = _make_portfolio(client, a_headers, "A", [{"symbol": "AAPL", "weight": 1.0}])
    assert (
        client.get(f"/api/portfolios/{a_pid}/valuations", headers=b_headers).status_code == 404
    )


def test_refresh_foreign_id_is_404(client):
    a_headers = auth_headers(client, "ref_a")
    b_headers = auth_headers(client, "ref_b")
    a_pid = _make_portfolio(client, a_headers, "A", [{"symbol": "AAPL", "weight": 1.0}])
    resp = client.post(
        f"/api/portfolios/{a_pid}/refresh", json={"start": "2021-01-04"}, headers=b_headers
    )
    assert resp.status_code == 404


def test_valuations_and_refresh_require_auth(client):
    assert client.get("/api/portfolios/1/valuations").status_code == 401
    assert client.post("/api/portfolios/1/refresh", json={}).status_code == 401
