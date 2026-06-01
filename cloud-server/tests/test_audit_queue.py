"""Tests for audit async queue and worker.

Covers:
- Async mode: audit_event enqueues to Redis instead of writing DB.
- Sync fallback: when Redis unavailable, falls back to DB write.
- Worker: dequeue + bulk insert into DB.
- Forbidden keys are still blocked in async mode.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class _FakeRedis:
    """Minimal Redis list stub for audit queue tests."""

    def __init__(self):
        self._lists: dict[str, list[str]] = {}

    def rpush(self, key: str, value: str) -> int:
        self._lists.setdefault(key, []).append(value)
        return len(self._lists[key])

    def lpop(self, key: str) -> str | None:
        lst = self._lists.get(key, [])
        if not lst:
            return None
        return lst.pop(0)

    def llen(self, key: str) -> int:
        return len(self._lists.get(key, []))


@pytest.fixture
def fake_redis():
    return _FakeRedis()


class TestAuditQueue:
    def test_enqueue_writes_to_redis(self, fake_redis):
        from app.services.audit_queue import enqueue_audit_event

        with patch("app.services.audit_queue._get_redis", return_value=fake_redis):
            enqueue_audit_event({"event": "test", "id": "1"})

        assert fake_redis.llen("zs:audit_events") == 1
        data = json.loads(fake_redis.lpop("zs:audit_events"))
        assert data["event"] == "test"

    def test_dequeue_batch_returns_events(self, fake_redis):
        from app.services.audit_queue import dequeue_batch

        # Pre-populate
        fake_redis.rpush("zs:audit_events", json.dumps({"event": "a", "id": "1"}))
        fake_redis.rpush("zs:audit_events", json.dumps({"event": "b", "id": "2"}))

        with patch("app.services.audit_queue._get_redis", return_value=fake_redis):
            events = dequeue_batch(10)

        assert len(events) == 2
        assert events[0]["event"] == "a"
        assert events[1]["event"] == "b"

    def test_dequeue_empty_returns_empty_list(self, fake_redis):
        from app.services.audit_queue import dequeue_batch

        with patch("app.services.audit_queue._get_redis", return_value=fake_redis):
            events = dequeue_batch(10)

        assert events == []

    def test_write_batch_to_db(self, db_session: Session, fake_redis):
        from app.services.audit_queue import write_batch_to_db
        from app.models.audit_log import utc_now

        now = utc_now()
        events = [
            {
                "id": str(uuid4()),
                "event": "login_success",
                "request_id": "req-1",
                "client_ip": "1.2.3.xxx",
                "user_id": str(uuid4()),
                "project_id": "",
                "backup_id": "",
                "result": "success",
                "reason_code": "",
                "extra_json": None,
                "created_at": now,
                "actor_user_id": None,
                "target_user_id": None,
                "client_ip_hash": None,
                "client_ip_masked": None,
            },
            {
                "id": str(uuid4()),
                "event": "backup_init",
                "request_id": "req-2",
                "client_ip": "1.2.3.xxx",
                "user_id": str(uuid4()),
                "project_id": "",
                "backup_id": "",
                "result": "success",
                "reason_code": "",
                "extra_json": None,
                "created_at": now,
                "actor_user_id": None,
                "target_user_id": None,
                "client_ip_hash": None,
                "client_ip_masked": None,
            },
        ]

        count = write_batch_to_db(events, db_session)
        assert count == 2

        rows = db_session.query(AuditLog).all()
        assert len(rows) == 2
        assert rows[0].event == "login_success"
        assert rows[1].event == "backup_init"

    def test_queue_length(self, fake_redis):
        from app.services.audit_queue import queue_length

        with patch("app.services.audit_queue._get_redis", return_value=fake_redis):
            assert queue_length() == 0
            fake_redis.rpush("zs:audit_events", json.dumps({"event": "x"}))
            assert queue_length() == 1


class TestAuditEventAsyncMode:
    def test_async_mode_enqueues_not_db(
        self, db_session: Session, fake_redis
    ):
        """When audit_async_enabled=True and Redis works, event goes to queue."""
        from app.core.audit import audit_event

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.services.audit_queue._get_redis", return_value=fake_redis),
        ):
            settings = MagicMock()
            settings.audit_async_enabled = True
            settings.audit_queue_name = "zs:audit_events"
            mock_settings.return_value = settings

            audit_event("login_success", db=db_session, user_id="u1")

        # Should be in Redis queue
        assert fake_redis.llen("zs:audit_events") == 1

        # Should NOT be in DB yet
        rows = db_session.query(AuditLog).all()
        assert len(rows) == 0

    def test_async_mode_fallback_on_redis_failure(
        self, db_session: Session
    ):
        """When Redis fails, falls back to sync DB write."""
        from app.core.audit import audit_event
        from app.services.audit_queue import AuditQueueError

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch(
                "app.services.audit_queue._get_redis",
                side_effect=AuditQueueError("Redis down"),
            ),
        ):
            settings = MagicMock()
            settings.audit_async_enabled = True
            mock_settings.return_value = settings

            audit_event("login_success", db=db_session, user_id="u1")

        # Should be in DB via fallback
        rows = db_session.query(AuditLog).all()
        assert len(rows) == 1
        assert rows[0].event == "login_success"

    def test_sync_mode_writes_directly(
        self, db_session: Session
    ):
        """When audit_async_enabled=False, write directly to DB."""
        from app.core.audit import audit_event

        with patch("app.core.config.get_settings") as mock_settings:
            settings = MagicMock()
            settings.audit_async_enabled = False
            mock_settings.return_value = settings

            audit_event("login_success", db=db_session, user_id="u1")

        rows = db_session.query(AuditLog).all()
        assert len(rows) == 1

    def test_forbidden_keys_blocked_in_async(
        self, db_session: Session, fake_redis
    ):
        """Forbidden keys must be stripped even in async mode."""
        from app.core.audit import audit_event

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.services.audit_queue._get_redis", return_value=fake_redis),
        ):
            settings = MagicMock()
            settings.audit_async_enabled = True
            mock_settings.return_value = settings

            audit_event(
                "login_success",
                db=db_session,
                extra={"password": "secret", "file_name": "test.zip"},
            )

        assert fake_redis.llen("zs:audit_events") == 1
        raw = fake_redis.lpop("zs:audit_events")
        payload = json.loads(raw)
        extra_data = json.loads(payload["extra_json"]) if payload.get("extra_json") else {}
        assert "password" not in extra_data
        assert extra_data.get("file_name") == "test.zip"

    def test_no_db_skips_persistence(self, db_session: Session, fake_redis):
        """When db=None, event is only logged (not persisted or enqueued)."""
        from app.core.audit import audit_event

        with (
            patch("app.core.config.get_settings") as mock_settings,
            patch("app.services.audit_queue._get_redis", return_value=fake_redis),
        ):
            settings = MagicMock()
            settings.audit_async_enabled = True
            mock_settings.return_value = settings

            audit_event("login_success")  # no db

        assert fake_redis.llen("zs:audit_events") == 0
        rows = db_session.query(AuditLog).all()
        assert len(rows) == 0
