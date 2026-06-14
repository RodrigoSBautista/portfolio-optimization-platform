"""Auth tests — password hashing + signup/login service (offline, in-memory DB)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from storage.auth_service import AuthError, AuthService
from storage.db import make_session_factory
from storage.models import Base
from storage.repository import Repository
from storage.security import hash_password, verify_password

# --- hashing --------------------------------------------------------------------

def test_hash_is_not_plaintext_and_verifies():
    h = hash_password("correct horse")
    assert h != "correct horse"
    assert verify_password("correct horse", h)


def test_verify_rejects_wrong_password():
    h = hash_password("secret123")
    assert not verify_password("wrong", h)


def test_verify_handles_malformed_hash():
    assert not verify_password("x", "not-a-real-hash")


def test_hash_rejects_overlong_password():
    with pytest.raises(ValueError, match="at most 72 bytes"):
        hash_password("a" * 73)


# --- auth service ---------------------------------------------------------------

@pytest.fixture
def repo():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    yield Repository(session)
    session.close()


def test_sign_up_then_authenticate(repo):
    svc = AuthService(repo)
    user = svc.sign_up("alice", "password1")
    assert user.id is not None
    assert svc.authenticate("alice", "password1").id == user.id


def test_authenticate_wrong_password_returns_none(repo):
    svc = AuthService(repo)
    svc.sign_up("alice", "password1")
    assert svc.authenticate("alice", "nope") is None


def test_authenticate_unknown_user_returns_none(repo):
    assert AuthService(repo).authenticate("ghost", "password1") is None


def test_sign_up_rejects_duplicate_username(repo):
    svc = AuthService(repo)
    svc.sign_up("alice", "password1")
    with pytest.raises(AuthError, match="already taken"):
        svc.sign_up("alice", "password2")


def test_sign_up_rejects_short_password(repo):
    with pytest.raises(AuthError, match="at least 8"):
        AuthService(repo).sign_up("bob", "short")


def test_sign_up_rejects_blank_username(repo):
    with pytest.raises(AuthError, match="required"):
        AuthService(repo).sign_up("   ", "password1")
