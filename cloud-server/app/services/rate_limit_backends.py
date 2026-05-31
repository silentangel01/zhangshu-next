"""Rate limit backend abstraction.

Two implementations are provided:

- :class:`DatabaseRateLimitBackend` — wraps the existing
  ``RateLimitRepository``. Suitable for development and as a fallback
  when Redis is unavailable.
- :class:`RedisRateLimitBackend` — fixed-window counter in Redis.
  Suitable for production; keys are hashed to avoid storing raw
  email/IP data.

Both backends implement the same protocol:
``check(scope, key, window_seconds) -> int`` returns the number of
events in the current window, and
``record(scope, key, window_seconds, user_id, client_ip)`` writes a
new event.

The service layer decides whether to raise ``RateLimitError`` based
on the count. This keeps backends free of circular imports with the
service module.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Protocol
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.security import sha256_text
from app.models.rate_limit_event import RateLimitEvent, utc_now
from app.repositories.rate_limit_repo import RateLimitRepository

logger = logging.getLogger(__name__)


class RateLimitBackend(Protocol):
    def count_active(
        self, scope: str, key: str, window_seconds: int
    ) -> int: ...

    def record(
        self,
        scope: str,
        key: str,
        window_seconds: int,
        *,
        user_id: str | None = None,
        client_ip: str | None = None,
    ) -> None: ...


class DatabaseRateLimitBackend:
    """Wrap the existing ``RateLimitRepository`` as a backend."""

    def __init__(self, db: Session):
        self._db = db
        self._repo = RateLimitRepository(db)

    def count_active(
        self, scope: str, key: str, window_seconds: int
    ) -> int:
        now = utc_now()
        window_start = now - timedelta(seconds=window_seconds)
        return self._repo.count_active(scope, key, window_start)

    def record(
        self,
        scope: str,
        key: str,
        window_seconds: int,
        *,
        user_id: str | None = None,
        client_ip: str | None = None,
    ) -> None:
        now = utc_now()
        event = RateLimitEvent(
            id=str(uuid4()),
            scope=scope,
            key=key,
            user_id=user_id,
            client_ip=client_ip,
            expires_at=now + timedelta(seconds=window_seconds),
        )
        self._repo.create(event)


class RedisRateLimitBackend:
    """Fixed-window rate limiter backed by Redis ``INCR`` + ``EXPIRE``.

    The key includes the window start timestamp so each window is a
    separate counter. ``EXPIRE`` is set slightly longer than the window
    to tolerate small clock drift.

    Keys are hashed — raw email addresses / IPs are never stored.
    """

    def __init__(self, redis_client) -> None:
        self._r = redis_client

    def _make_redis_key(
        self, scope: str, key: str, window_seconds: int
    ) -> str:
        window_start = int(time.time()) // window_seconds
        hashed = sha256_text(f"{scope}:{key}")[:24]
        return f"rl:{scope}:{hashed}:{window_start}"

    def count_active(
        self, scope: str, key: str, window_seconds: int
    ) -> int:
        # Look at the current window — we don't need to write anything
        redis_key = self._make_redis_key(scope, key, window_seconds)
        try:
            raw = self._r.get(redis_key)
        except Exception as exc:
            logger.warning("Redis rate limit GET failed: %s", exc)
            raise
        if raw is None:
            return 0
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    def record(
        self,
        scope: str,
        key: str,
        window_seconds: int,
        *,
        user_id: str | None = None,
        client_ip: str | None = None,
    ) -> None:
        redis_key = self._make_redis_key(scope, key, window_seconds)
        try:
            count = self._r.incr(redis_key)
            if count == 1:
                self._r.expire(redis_key, window_seconds + 5)
        except Exception as exc:
            logger.warning("Redis rate limit INCR failed: %s", exc)
            raise
