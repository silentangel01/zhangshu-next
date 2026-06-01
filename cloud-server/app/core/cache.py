"""Cache backend abstraction.

Provides two implementations:

- :class:`MemoryCacheBackend` — process-local, suitable for development
  and tests.
- :class:`RedisCacheBackend` — shared across workers and instances,
  suitable for production.

Both expose the same small surface:

- ``get_json(key)`` → ``dict | None``
- ``set_json(key, value, ttl_seconds)`` → ``None``
- ``delete(key)`` → ``None``
- ``acquire_lock(key, ttl_seconds)`` → context manager yielding ``bool``

Callers should use :func:`get_cache_backend` to obtain the configured
backend rather than constructing implementations directly.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)


class CacheBackend:
    """Abstract cache backend. Subclasses must override all methods."""

    def get_json(self, key: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def set_json(
        self, key: str, value: dict[str, Any], ttl_seconds: int
    ) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    @contextmanager
    def acquire_lock(self, key: str, ttl_seconds: int):
        raise NotImplementedError
        yield  # pragma: no cover


class MemoryCacheBackend(CacheBackend):
    """In-process cache with TTL based on monotonic clock."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}
        self._locks: dict[str, bool] = {}  # key → held flag
        self._meta_lock = threading.Lock()

    def _now(self) -> float:
        return time.monotonic()

    def get_json(self, key: str) -> dict[str, Any] | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, payload = entry
        if self._now() > expires_at:
            self._store.pop(key, None)
            return None
        try:
            return json.loads(payload)
        except (TypeError, ValueError):
            return None

    def set_json(
        self, key: str, value: dict[str, Any], ttl_seconds: int
    ) -> None:
        payload = json.dumps(value, ensure_ascii=False)
        expires_at = self._now() + max(1, ttl_seconds)
        self._store[key] = (expires_at, payload)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    @contextmanager
    def acquire_lock(self, key: str, ttl_seconds: int):
        with self._meta_lock:
            held = self._locks.get(key, False)
            if held:
                yield False
                return
            self._locks[key] = True
        try:
            yield True
        finally:
            with self._meta_lock:
                self._locks[key] = False


class RedisCacheBackend(CacheBackend):
    """Redis-backed cache. Failures are logged and surfaced as None / False."""

    def __init__(self, redis_client) -> None:
        self._r = redis_client

    def get_json(self, key: str) -> dict[str, Any] | None:
        try:
            payload = self._r.get(key)
        except Exception as exc:
            logger.warning("Redis GET %s failed: %s", key, exc)
            return None
        if payload is None:
            return None
        try:
            return json.loads(payload)
        except (TypeError, ValueError):
            return None

    def set_json(
        self, key: str, value: dict[str, Any], ttl_seconds: int
    ) -> None:
        try:
            payload = json.dumps(value, ensure_ascii=False)
            self._r.set(key, payload, ex=max(1, ttl_seconds))
        except Exception as exc:
            logger.warning("Redis SET %s failed: %s", key, exc)

    def delete(self, key: str) -> None:
        try:
            self._r.delete(key)
        except Exception as exc:
            logger.warning("Redis DEL %s failed: %s", key, exc)

    @contextmanager
    def acquire_lock(self, key: str, ttl_seconds: int):
        lock_key = f"lock:{key}"
        acquired = False
        try:
            acquired = bool(
                self._r.set(lock_key, "1", nx=True, ex=max(1, ttl_seconds))
            )
        except Exception as exc:
            logger.warning("Redis acquire_lock %s failed: %s", lock_key, exc)
            acquired = False
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    self._r.delete(lock_key)
                except Exception:
                    pass


def get_cache_backend() -> CacheBackend:
    """Return the configured cache backend based on settings."""
    from app.core.config import get_settings

    settings = get_settings()
    if settings.cache_backend == "redis":
        try:
            from app.core.redis_client import get_redis_client

            client = get_redis_client()
            return RedisCacheBackend(client)
        except Exception as exc:
            logger.warning(
                "Redis cache backend unavailable, falling back to memory: %s",
                exc,
            )
    return MemoryCacheBackend()
