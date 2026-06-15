"""API portfolio tests — CRUD and the critical per-user isolation guarantee."""

from __future__ import annotations

import pytest

from tests.api_helpers import auth_headers, build_client


@pytest.fixture
def client():
    client, teardown = build_client()
    yield client
    teardown()


SAMPLE_SPEC = {
    "name": "My Portfolio",
    "benchmark_symbol": "SPY",
    "base_currency": "USD",
    "holdings": [
        {"symbol": "AAPL", "weight": 0.6},
        {"symbol": "MSFT", "weight": 0.4},
    ],
    "contributions": [{"kind": "lump_sum", "amount": 1000.0}],
}


def test_tickers_endpoint(client):
    headers = auth_headers(client, "tick")
    resp = client.get("/api/tickers", headers=headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert rows and {"symbol", "name"} <= set(rows[0])


def test_create_list_get_delete(client):
    headers = auth_headers(client, "owner")
    created = client.post("/api/portfolios", json=SAMPLE_SPEC, headers=headers)
    assert created.status_code == 201
    pid = created.json()["id"]
    assert created.json()["name"] == "My Portfolio"
    assert len(created.json()["holdings"]) == 2

    listed = client.get("/api/portfolios", headers=headers)
    assert listed.status_code == 200
    assert [p["id"] for p in listed.json()] == [pid]

    got = client.get(f"/api/portfolios/{pid}", headers=headers)
    assert got.status_code == 200

    deleted = client.delete(f"/api/portfolios/{pid}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/portfolios/{pid}", headers=headers).status_code == 404


def test_per_user_isolation(client):
    """User A's portfolio is invisible and inaccessible to user B."""
    a_headers = auth_headers(client, "user_a")
    b_headers = auth_headers(client, "user_b")

    created = client.post("/api/portfolios", json=SAMPLE_SPEC, headers=a_headers)
    a_pid = created.json()["id"]

    # B cannot read A's portfolio by id.
    assert client.get(f"/api/portfolios/{a_pid}", headers=b_headers).status_code == 404
    # ...nor delete it.
    assert client.delete(f"/api/portfolios/{a_pid}", headers=b_headers).status_code == 404
    # ...and it never appears in B's list.
    b_list = client.get("/api/portfolios", headers=b_headers)
    assert b_list.json() == []
    # A still sees it.
    a_list = client.get("/api/portfolios", headers=a_headers)
    assert [p["id"] for p in a_list.json()] == [a_pid]


def test_portfolios_require_auth(client):
    assert client.get("/api/portfolios").status_code == 401
