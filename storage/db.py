"""Database engine/session factory — DB-agnostic via the SQLAlchemy URL.

Phase 1 defaults to local SQLite; the same code targets PostgreSQL later by
changing only ``DATABASE_URL``. No model rewrite required.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///portfolio.db"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_db_engine(url: str | None = None) -> Engine:
    url = url or database_url()
    # check_same_thread=False lets Streamlit's threads share a SQLite connection.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, future=True, connect_args=connect_args)

    if url.startswith("sqlite"):
        # SQLite ignores foreign keys unless this pragma is set per connection;
        # turn it on so the DB enforces FK/cascade integrity, not just the ORM.
        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_connection, _record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Transactional session scope: commit on success, roll back on error."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
