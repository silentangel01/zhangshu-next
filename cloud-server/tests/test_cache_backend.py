"""Tests for cache backend abstraction.

Covers:
- MemoryCacheBackend: read/write JSON, TTL expiry, delete, lock semantics.
- RedisCacheBackend: exception wrapping (fake Redis that raises).
- Lock: not-held → acquired; already-held → not acquired (non-blocking).
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from app.core.cache import CacheBackend, MemoryCacheBackend, RedisCacheBackend


class TestMemoryCacheBackend:
    def test_set_and_get_json(self):
        cache = MemoryCacheBackend()
        cache.set_json("k", {"v": 1}, ttl_seconds=60)
        result = cache.get_json("k")
        assert result == {"v": 1}

    def test_get_missing_returns_none(self):
        cache = MemoryCacheBackend()
        assert cache.get_json("missing") is None

    def test_ttl_expiry(self):
        cache = MemoryCacheBackend()
        cache.set_json("k", {"v": 1}, ttl_seconds=0)
        # ttl_seconds=0 → max(1, 0) = 1 second
        # We need to wait > 1 second for it to expire
        time.sleep(1.1)
        assert cache.get_json("k") is None

    def test_delete(self):
        cache = MemoryCacheBackend()
        cache.set_json("k", {"v": 1}, ttl_seconds=60)
        cache.delete("k")
        assert cache.get_json("k") is None

    def test_delete_missing_is_noop(self):
        cache = MemoryCacheBackend()
        cache.delete("nope")  # should not raise

    def test_lock_acquired_when_not_held(self):
        cache = MemoryCacheBackend()
        with cache.acquire_lock("mylock", ttl_seconds=5) as acquired:
            assert acquired is True

    def test_lock_not_acquired_when_held(self):
        cache = MemoryCacheBackend()
        with cache.acquire_lock("mylock", ttl_seconds=5) as acquired:
            assert acquired is True
            # Nested attempt should fail
            with cache.acquire_lock("mylock", ttl_seconds=5) as inner:
                assert inner is False

    def test_lock_released_after_context(self):
        cache = MemoryCacheBackend()
        with cache.acquire_lock("mylock", ttl_seconds=5):
            pass
        # Lock should be available again
        with cache.acquire_lock("mylock", ttl_seconds=5) as acquired:
            assert acquired is True


class TestRedisCacheBackend:
    def test_get_json_success(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = b'{"a": 1}'
        cache = RedisCacheBackend(mock_redis)
        assert cache.get_json("k") == {"a": 1}

    def test_get_json_missing(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        cache = RedisCacheBackend(mock_redis)
        assert cache.get_json("k") is None

    def test_get_json_redis_error_returns_none(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")
        cache = RedisCacheBackend(mock_redis)
        assert cache.get_json("k") is None

    def test_set_json_calls_redis(self):
        mock_redis = MagicMock()
        cache = RedisCacheBackend(mock_redis)
        cache.set_json("k", {"b": 2}, ttl_seconds=30)
        mock_redis.set.assert_called_once()

    def test_set_json_redis_error_does_not_raise(self):
        mock_redis = MagicMock()
        mock_redis.set.side_effect = ConnectionError("Redis down")
        cache = RedisCacheBackend(mock_redis)
        cache.set_json("k", {"b": 2}, ttl_seconds=30)  # should not raise

    def test_delete_redis_error_does_not_raise(self):
        mock_redis = MagicMock()
        mock_redis.delete.side_effect = ConnectionError("Redis down")
        cache = RedisCacheBackend(mock_redis)
        cache.delete("k")  # should not raise

    def test_lock_acquired_via_set_nx(self):
        mock_redis = MagicMock()
        mock_redis.set.return_value = True  # NX succeeded
        cache = RedisCacheBackend(mock_redis)
        with cache.acquire_lock("mylock", ttl_seconds=5) as acquired:
            assert acquired is True
        mock_redis.delete.assert_called()

    def test_lock_not_acquired_when_nx_fails(self):
        mock_redis = MagicMock()
        mock_redis.set.return_value = None  # NX failed (key exists)
        cache = RedisCacheBackend(mock_redis)
        with cache.acquire_lock("mylock", ttl_seconds=5) as acquired:
            assert acquired is False

    def test_lock_redis_error_yields_false(self):
        mock_redis = MagicMock()
        mock_redis.set.side_effect = ConnectionError("Redis down")
        cache = RedisCacheBackend(mock_redis)
        with cache.acquire_lock("mylock", ttl_seconds=5) as acquired:
            assert acquired is False
