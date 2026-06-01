"""Tests for Redis rate limit backend and fallback behavior.

Uses a fake Redis implementation so no real Redis instance is required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeRedis:
    """In-memory fake of the subset of ``redis.Redis`` used by the backend."""

    def __init__(self) -> None:
        self._store: dict[str, int] = {}
        self._ttls: dict[str, int] = {}
        self.fail_on_next = False

    def get(self, key: str):
        if self.fail_on_next:
            raise ConnectionError("simulated redis failure")
        return self._store.get(key)

    def incr(self, key: str) -> int:
        if self.fail_on_next:
            raise ConnectionError("simulated redis failure")
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key]

    def expire(self, key: str, seconds: int) -> None:
        self._ttls[key] = seconds


class TestRedisRateLimitBackend:
    def test_count_returns_zero_when_empty(self):
        from app.services.rate_limit_backends import RedisRateLimitBackend

        backend = RedisRateLimitBackend(FakeRedis())
        assert backend.count_active("scope", "key", 60) == 0

    def test_record_increments_and_expires(self):
        from app.services.rate_limit_backends import RedisRateLimitBackend

        fake = FakeRedis()
        backend = RedisRateLimitBackend(fake)
        backend.record("scope", "key", 60)
        assert backend.count_active("scope", "key", 60) == 1

    def test_key_does_not_contain_raw_email(self):
        from app.services.rate_limit_backends import RedisRateLimitBackend

        fake = FakeRedis()
        backend = RedisRateLimitBackend(fake)
        backend.record("auth_login", "user@example.com", 60)
        # All keys stored in fake._store should not contain the raw email
        for key in fake._store:
            assert "user@example.com" not in key
            assert "example.com" not in key


class TestRateLimitServiceWithRedis:
    @pytest.fixture
    def db_session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.db.base import Base

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        try:
            yield session
        finally:
            session.close()
            Base.metadata.drop_all(engine)

    def test_raises_when_limit_exceeded_via_redis(self, db_session, monkeypatch):
        from app.services.rate_limit_service import RateLimitError, RateLimitService

        # Force redis backend by settings
        monkeypatch.setattr(
            "app.core.config.Settings.rate_limit_backend", "redis",
            raising=False,
        )
        monkeypatch.setattr(
            "app.core.config.Settings.redis_enabled", True, raising=False,
        )

        fake = FakeRedis()

        def _fake_get_client():
            return fake

        import app.core.redis_client as rc

        monkeypatch.setattr(rc, "get_redis_client", _fake_get_client)

        svc = RateLimitService(db_session)
        svc.check_and_record("scope", "key", limit=2, window_seconds=60)
        svc.check_and_record("scope", "key", limit=2, window_seconds=60)
        with pytest.raises(RateLimitError):
            svc.check_and_record("scope", "key", limit=2, window_seconds=60)

    def test_falls_back_to_db_on_redis_failure(self, db_session, monkeypatch):
        from app.services.rate_limit_service import RateLimitService

        monkeypatch.setattr(
            "app.core.config.Settings.rate_limit_backend", "redis",
            raising=False,
        )
        monkeypatch.setattr(
            "app.core.config.Settings.redis_enabled", True, raising=False,
        )

        fake = FakeRedis()
        fake.fail_on_next = True  # Simulate Redis down

        def _fake_get_client():
            return fake

        import app.core.redis_client as rc

        monkeypatch.setattr(rc, "get_redis_client", _fake_get_client)

        svc = RateLimitService(db_session)
        # Should not raise — falls back to DB backend
        svc.check_and_record("scope", "key", limit=5, window_seconds=60)
        svc.check_and_record("scope", "key", limit=5, window_seconds=60)

    def test_uses_db_backend_when_configured(self, db_session, monkeypatch):
        from app.services.rate_limit_service import RateLimitError, RateLimitService

        monkeypatch.setattr(
            "app.core.config.Settings.rate_limit_backend", "database",
            raising=False,
        )

        svc = RateLimitService(db_session)
        assert svc._use_redis is False
        svc.check_and_record("scope", "key", limit=2, window_seconds=60)
        svc.check_and_record("scope", "key", limit=2, window_seconds=60)
        with pytest.raises(RateLimitError):
            svc.check_and_record("scope", "key", limit=2, window_seconds=60)
