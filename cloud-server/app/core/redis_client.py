"""Unified Redis client.

Provides ``get_redis_client()`` that returns a ready-to-use ``redis.Redis``
instance configured with short connect/read timeouts. Callers must be
prepared for ``RedisUnavailable`` when Redis is disabled or unreachable.

``check_redis_health()`` is used by the ``/ready`` endpoint to report
Redis status without raising on connection failure.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisUnavailable(RuntimeError):
    """Raised when Redis is disabled or unreachable."""


_client = None


def get_redis_client():
    """Return a shared ``redis.Redis`` instance.

    Raises :class:`RedisUnavailable` when ``redis_enabled`` is False or
    the ``redis`` package is not installed. Connection errors during
    first use will propagate to callers — callers should handle them.
    """
    settings = get_settings()
    if not settings.redis_enabled:
        raise RedisUnavailable("Redis is disabled (REDIS_ENABLED=false).")

    try:
        import redis
    except ImportError as exc:  # pragma: no cover - redis is in requirements
        raise RedisUnavailable("redis package is not installed.") from exc

    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
    return _client


def check_redis_health() -> dict[str, Any]:
    """Return a health dict for the ``/ready`` endpoint.

    Always returns — never raises. Reports ``"ok"``, ``"disabled"``,
    or ``"error: <message>"``.
    """
    settings = get_settings()
    if not settings.redis_enabled:
        return {"status": "disabled"}

    try:
        client = get_redis_client()
        pong = client.ping()
        if pong:
            return {"status": "ok"}
        return {"status": "error: ping returned falsy"}
    except RedisUnavailable as exc:
        return {"status": f"error: {exc}"}
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Redis health check failed: %s", exc)
        return {"status": f"error: {exc}"}


def reset_client_for_tests() -> None:
    """Clear the cached client. Used by tests between fixtures."""
    global _client
    _client = None
