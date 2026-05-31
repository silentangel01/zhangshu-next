"""Tests for admin metric snapshot service.

Covers:
- First request computes and store snapshot.
- Cache hit returns without recomputing.
- Stale snapshot served when lock not acquired.
- No snapshot and no cache → live compute fallback.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.cache import MemoryCacheBackend
from app.models.admin_metric_snapshot import AdminMetricSnapshot
from app.models.user import utc_now
from app.services.admin_metric_snapshot_service import AdminMetricSnapshotService


class TestAdminMetricSnapshotService:
    def _make_service(self, db_session: Session) -> AdminMetricSnapshotService:
        cache = MemoryCacheBackend()
        return AdminMetricSnapshotService(db_session, cache=cache), cache

    def test_first_request_computes_and_caches(
        self, db_session: Session
    ):
        svc, cache = self._make_service(db_session)
        call_count = 0

        def compute():
            nonlocal call_count
            call_count += 1
            return {"total_users": 42}

        result = svc.get_or_refresh("summary", compute, ttl_seconds=60)

        assert call_count == 1
        assert result["total_users"] == 42
        assert result["cached"] is False
        assert result["stale"] is False
        assert "refreshed_at" in result

        # Cache should now have the entry
        cached = cache.get_json("admin_metrics:summary")
        assert cached is not None
        assert cached["total_users"] == 42

    def test_cache_hit_skips_compute(self, db_session: Session):
        svc, cache = self._make_service(db_session)
        call_count = 0

        def compute():
            nonlocal call_count
            call_count += 1
            return {"total_users": 10}

        # First call — populate
        svc.get_or_refresh("summary", compute, ttl_seconds=60)
        assert call_count == 1

        # Second call — should hit cache
        result = svc.get_or_refresh("summary", compute, ttl_seconds=60)
        assert call_count == 1  # not called again
        assert result["cached"] is True
        assert result["stale"] is False
        assert result["total_users"] == 10

    def test_stale_snapshot_when_lock_not_acquired(
        self, db_session: Session
    ):
        """When the cache is empty and the lock is held by another worker,
        we should serve the stale DB snapshot."""
        svc, cache = self._make_service(db_session)

        # Pre-populate a DB snapshot (simulating a previous refresh)
        now = utc_now()
        db_session.add(
            AdminMetricSnapshot(
                key="summary",
                payload_json=json.dumps(
                    {"total_users": 99, "refreshed_at": now.isoformat()}
                ),
                refreshed_at=now,
                expires_at=now + timedelta(seconds=600),
            )
        )
        db_session.commit()

        # Hold the lock to simulate another worker refreshing
        with cache.acquire_lock("admin_metrics:summary", ttl_seconds=30) as acquired:
            assert acquired is True
            # Now create a NEW service (same cache) and try to get_or_refresh
            # The lock is already held, so it should serve stale
            svc2 = AdminMetricSnapshotService(db_session, cache=cache)

            def compute():
                raise AssertionError("Should not compute when lock is held")

            result = svc2.get_or_refresh("summary", compute, ttl_seconds=60)
            assert result["cached"] is True
            assert result["stale"] is True
            assert result["total_users"] == 99

    def test_no_snapshot_no_cache_computes_live(
        self, db_session: Session
    ):
        """When there's no cache and no DB snapshot, compute live."""
        svc, cache = self._make_service(db_session)

        # Hold the lock to force the stale path
        with cache.acquire_lock("admin_metrics:summary", ttl_seconds=30) as acquired:
            assert acquired is True
            svc2 = AdminMetricSnapshotService(db_session, cache=cache)

            def compute():
                return {"total_users": 7}

            # No DB snapshot exists, so it must compute live
            result = svc2.get_or_refresh("summary", compute, ttl_seconds=60)
            assert result["total_users"] == 7
            assert result["cached"] is False
            assert result["stale"] is False

    def test_db_snapshot_persisted(self, db_session: Session):
        svc, _cache = self._make_service(db_session)

        svc.get_or_refresh("summary", lambda: {"total_users": 55}, ttl_seconds=60)

        snapshot = (
            db_session.query(AdminMetricSnapshot)
            .filter_by(key="summary")
            .one_or_none()
        )
        assert snapshot is not None
        payload = json.loads(snapshot.payload_json)
        assert payload["total_users"] == 55
        assert "refreshed_at" in payload

    def test_db_snapshot_updated_on_refresh(self, db_session: Session):
        svc, cache = self._make_service(db_session)

        svc.get_or_refresh("summary", lambda: {"total_users": 1}, ttl_seconds=60)

        # Invalidate cache to force recompute
        cache.delete("admin_metrics:summary")

        svc.get_or_refresh("summary", lambda: {"total_users": 2}, ttl_seconds=60)

        snapshot = (
            db_session.query(AdminMetricSnapshot)
            .filter_by(key="summary")
            .one()
        )
        payload = json.loads(snapshot.payload_json)
        assert payload["total_users"] == 2
