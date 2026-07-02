"""API auth tests: signup/login issue a JWT; /me requires a valid Bearer token."""

from __future__ import annotations

import pytest

from tests.api_helpers import auth_headers, build_client


@pytest.fixture
def client():
    client, teardown = build_client()
    yield client
    teardown()


def test_root_and_health_are_browsable(client):
    # Opening the API base URL in a browser should explain itself, not 404.
    root = client.get("/")
    assert root.status_code == 200
    assert "5173" in root.json()["hint"]
    assert client.get("/api/health").json() == {"status": "ok"}


def test_signup_then_login_returns_jwt(client):
    signup = client.post("/api/auth/signup", json={"username": "alice", "password": "password123"})
    assert signup.status_code == 200
    assert signup.json()["token_type"] == "bearer"
    assert signup.json()["access_token"]

    login = client.post("/api/auth/login", json={"username": "alice", "password": "password123"})
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_me_works_with_token(client):
    headers = auth_headers(client, "bob")
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "bob"
    assert isinstance(resp.json()["id"], int)


def test_me_without_token_is_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_garbage_token_is_401(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_duplicate_signup_is_400(client):
    client.post("/api/auth/signup", json={"username": "carol", "password": "password123"})
    dup = client.post("/api/auth/signup", json={"username": "carol", "password": "password123"})
    assert dup.status_code == 400


def test_short_password_is_400(client):
    resp = client.post("/api/auth/signup", json={"username": "dave", "password": "short"})
    assert resp.status_code == 400


def test_wrong_password_is_401(client):
    client.post("/api/auth/signup", json={"username": "erin", "password": "password123"})
    resp = client.post("/api/auth/login", json={"username": "erin", "password": "wrongpass1"})
    assert resp.status_code == 401
