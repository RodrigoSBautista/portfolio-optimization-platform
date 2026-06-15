"""Shared helpers for the API tests: offline TestClient with a temp DB + fake prices.

Keeps API tests fully offline and deterministic by overriding the price-service
dependency with a synthetic provider, and isolated by pointing the session factory at
a fresh in-memory SQLite engine (shared connection across requests).
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api import deps
from api.main import app
from data.prices import PriceService
from storage.db import make_session_factory
from storage.models import Base


class FakeProvider:
    """Deterministic synthetic adjusted-close prices — no network.

    Each ticker is a smooth geometric series with a per-ticker drift derived from its
    name, so weights/metrics differ between tickers but are reproducible.
    """

    def fetch_adjusted_close(
        self, tickers: list[str], start: date, end: date | None = None
    ) -> pd.DataFrame:
        idx = pd.date_range(start=pd.Timestamp(start), periods=260, freq="B")
        data = {}
        for t in tickers:
            seed = sum(ord(c) for c in t.upper())
            rng = np.random.default_rng(seed)
            drift = 0.0002 + (seed % 7) * 0.00005
            shocks = rng.normal(drift, 0.01, size=len(idx))
            prices = 100.0 * np.exp(np.cumsum(shocks))
            data[t.upper()] = prices
        return pd.DataFrame(data, index=idx)


def build_client():
    """Return (TestClient, teardown) wired to a temp in-memory DB and fake prices."""
    from fastapi.testclient import TestClient

    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared in-memory connection across requests
    )
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)

    app.dependency_overrides[deps.get_session_factory] = lambda: factory
    app.dependency_overrides[deps.get_price_service] = lambda: PriceService(provider=FakeProvider())

    client = TestClient(app)

    def teardown():
        app.dependency_overrides.clear()
        engine.dispose()

    return client, teardown


def auth_headers(client, username: str, password: str = "password123") -> dict[str, str]:
    """Sign up a user and return an Authorization header for them."""
    resp = client.post("/api/auth/signup", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
