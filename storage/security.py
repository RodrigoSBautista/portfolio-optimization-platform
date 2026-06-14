"""Password hashing — bcrypt, framework-free.

Used by the auth service; no Streamlit/DB imports. bcrypt silently truncates input
beyond 72 bytes, so we reject longer passwords rather than hash a truncated secret.
"""

from __future__ import annotations

import bcrypt

MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    _check_length(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _check_length(password: str) -> None:
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
