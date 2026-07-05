"""Alembic migration round-trip — the lots migration must upgrade AND downgrade.

Runs the whole chain against a throwaway file-based SQLite so a broken up/down (the
classic "autogenerate forgot the downgrade") is caught in CI, not in production during
the SQLite -> Postgres move.
"""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_ROOT = Path(__file__).resolve().parents[1]


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_ROOT / "migrations"))
    # env.py reads DATABASE_URL; set it on the config too so this is self-contained.
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_lots_migration_up_down_round_trip(tmp_path, monkeypatch):
    db = tmp_path / "scratch.db"
    url = f"sqlite:///{db}"
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = _alembic_config(url)
    engine = sa.create_engine(url)

    # Upgrade to head: every table (including lots) exists.
    command.upgrade(cfg, "head")
    tables = set(sa.inspect(engine).get_table_names())
    assert "lots" in tables
    assert {"users", "portfolios", "holdings", "contributions", "daily_valuations"} <= tables

    cols = {c["name"] for c in sa.inspect(engine).get_columns("lots")}
    assert cols == {"id", "portfolio_id", "symbol", "purchase_date", "amount"}

    # Downgrade one step: the lots table is dropped, the rest survives.
    command.downgrade(cfg, "-1")
    tables = set(sa.inspect(engine).get_table_names())
    assert "lots" not in tables
    assert "portfolios" in tables

    # Upgrade again: idempotent re-apply works (no leftover state).
    command.upgrade(cfg, "head")
    assert "lots" in set(sa.inspect(engine).get_table_names())
    engine.dispose()
