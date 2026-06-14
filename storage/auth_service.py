"""Authentication service — signup/login on top of the repository.

Framework-free (no Streamlit). Ties the user repository to password hashing and
enforces basic rules (unique username, minimum password length). The Streamlit UI
in ``app/auth.py`` calls this within a session scope.
"""

from __future__ import annotations

from storage.models import User
from storage.repository import Repository
from storage.security import hash_password, verify_password

MIN_PASSWORD_LENGTH = 8


class AuthError(Exception):
    """Raised for user-facing auth problems (bad input, taken username)."""


class AuthService:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def sign_up(self, username: str, password: str) -> User:
        username = (username or "").strip()
        if not username:
            raise AuthError("Username is required.")
        if len(password or "") < MIN_PASSWORD_LENGTH:
            raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if self.repo.get_user_by_username(username) is not None:
            raise AuthError("That username is already taken.")
        return self.repo.create_user(username, hash_password(password))

    def authenticate(self, username: str, password: str) -> User | None:
        user = self.repo.get_user_by_username((username or "").strip())
        if user is not None and verify_password(password, user.password_hash):
            return user
        return None
