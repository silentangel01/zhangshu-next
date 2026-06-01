"""JWT token creation and verification."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from app.core.config import get_settings
from app.core.security import sha256_text

# UTC+8 — 与 model 层 utc_now() 保持一致
_CST = timezone(timedelta(hours=8))


class TokenError(Exception):
    """Raised when token operations fail."""


def _settings():
    return get_settings()


def _now_aware():
    """Aware UTC+8 datetime — used for JWT payload (PyJWT requires aware)."""
    return datetime.now(_CST)


def _now_naive():
    """Naive UTC+8 datetime — used for DB storage (SQLite safe)."""
    return datetime.now(_CST).replace(tzinfo=None)


def create_access_token(user_id: str) -> str:
    s = _settings()
    now = _now_aware()
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=s.jwt_access_token_expire_minutes),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """Return ``(token, jti, expires_at)``.

    ``expires_at`` is naive UTC+8 for SQLite compatibility.
    """
    s = _settings()
    now = _now_aware()
    expires_at = _now_naive() + timedelta(days=s.jwt_refresh_token_expire_days)
    jti = str(uuid4())
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=s.jwt_refresh_token_expire_days),
        "jti": jti,
    }
    token = jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)
    return token, jti, expires_at


def decode_token(token: str, expected_type: str) -> dict:
    """Decode and validate a JWT token. Raises ``TokenError`` on failure."""
    s = _settings()
    try:
        payload = jwt.decode(
            token, s.jwt_secret_key, algorithms=[s.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token 已过期。") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("无效的 Token。") from exc

    if payload.get("type") != expected_type:
        raise TokenError("Token 类型不匹配。")

    return payload


def hash_jti(jti: str) -> str:
    """Hash a JTI for storage in the database."""
    return sha256_text(jti)


# ------------------------------------------------------------------
# Admin tokens (shorter-lived, used in HttpOnly cookies)
# ------------------------------------------------------------------


def create_admin_access_token(user_id: str) -> str:
    s = _settings()
    now = _now_aware()
    payload = {
        "sub": user_id,
        "type": "admin_access",
        "iat": now,
        "exp": now + timedelta(minutes=s.admin_access_token_expire_minutes),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)


def create_admin_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """Return ``(token, jti, expires_at)`` for admin refresh cookie."""
    s = _settings()
    now = _now_aware()
    expires_at = _now_naive() + timedelta(hours=s.admin_refresh_token_expire_hours)
    jti = str(uuid4())
    payload = {
        "sub": user_id,
        "type": "admin_refresh",
        "iat": now,
        "exp": now + timedelta(hours=s.admin_refresh_token_expire_hours),
        "jti": jti,
    }
    token = jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)
    return token, jti, expires_at
