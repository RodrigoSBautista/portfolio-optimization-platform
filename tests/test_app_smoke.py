"""Headless boot smoke test — the app starts and shows the login screen, no errors."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_app_boots_to_login(tmp_path, monkeypatch):
    db = (tmp_path / "app.db").as_posix()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")

    at = AppTest.from_file("app/streamlit_app.py", default_timeout=60).run()

    assert not at.exception
    # Logged out -> login screen with the app title is shown (pages are gated).
    assert any("Portfolio Platform" in t.value for t in at.title)
