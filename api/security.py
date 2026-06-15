"""JWT encode/decode for the API (PyJWT, HS256).

The signing secret comes from the ``AUTH_SECRET`` env var with a dev-only default;
set a real secret in production. Tokens carry the user id as ``sub`` and expire.
"""

from __future__ import annotations

import os
import warnings
from datetime import UTC, datetime, timedelta

import jwt

ALGORITHM = "HS256"
# 32+ bytes so PyJWT doesn't warn on HS256; replace via AUTH_SECRET in production.
DEV_SECRET = "dev-insecure-secret-change-me-in-production-please"  # noqa: S105
DEFAULT_EXPIRY_MINUTES = 60 * 24  # 24h
_warned = False


def _secret() -> str:
    """Signing secret. Requires AUTH_SECRET in production; warns (once) in dev.

    Falling back to a public hardcoded secret in production would let anyone forge a
    token for any user, so production (``APP_ENV=prod``) must set ``AUTH_SECRET``.
    """
    secret = os.environ.get("AUTH_SECRET")
    if secret:
        return secret
    if os.environ.get("APP_ENV", "").lower() in {"prod", "production"}:
        raise RuntimeError("AUTH_SECRET must be set when APP_ENV is production.")
    global _warned
    if not _warned:
        warnings.warn(
            "AUTH_SECRET not set — using an insecure dev secret. Fine for local dev; "
            "never use in production (set AUTH_SECRET).",
            stacklevel=2,
        )
        _warned = True
    return DEV_SECRET


def create_access_token(user_id: int, *, expires_minutes: int = DEFAULT_EXPIRY_MINUTES) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """Decode a token and return the user id; raises ``jwt.PyJWTError`` if invalid."""
    payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    return int(payload["sub"])
