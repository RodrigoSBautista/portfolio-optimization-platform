"""FastAPI dependencies: DB session, price service, and the current user.

The engine/session factory and the price service are process singletons created
lazily, so tests can override them (``app.dependency_overrides``) to stay offline and
use a temp database. ``Base.metadata.create_all`` runs on startup for dev convenience
(Alembic owns real migrations).
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.security import decode_access_token
from data.prices import PriceService
from storage.db import create_db_engine, make_session_factory
from storage.models import Base, User
from storage.repository import Repository

_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_session_factory():
    """Process-wide session factory; creates tables on first use (dev convenience)."""
    engine = create_db_engine()
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


@lru_cache(maxsize=1)
def get_price_service() -> PriceService:
    """Process-wide price service (no parquet cache by default for API simplicity)."""
    return PriceService()


def get_session(factory=Depends(get_session_factory)) -> Iterator[Session]:
    """Per-request transactional session: commit on success, roll back on error."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_repository(session: Session = Depends(get_session)) -> Repository:
    return Repository(session)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    repo: Repository = Depends(get_repository),
) -> User:
    """Decode the Bearer JWT and load the user; 401 on any failure."""
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or not credentials.credentials:
        raise invalid
    try:
        user_id = decode_access_token(credentials.credentials)
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise invalid from exc
    user = repo.get_user(user_id)
    if user is None:
        raise invalid
    return user
