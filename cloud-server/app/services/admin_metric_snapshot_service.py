"""Admin metric snapshot service — cache + DB snapshot + live fallback.

Priority chain for ``get_or_refresh()``:

1. **Cache** (Redis or memory) — fastest, shared across workers.
2. **DB snapshot** — survives cache eviction, slightly stale.
3. **Live compute** — last resort when nothing is cached.

When the cache entry expires, only one worker acquires the lock and
recomputes.  Other workers return the stale DB snapshot (marked
``stale=True``) instead of all recomputing simultaneously.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.models.admin_metric_snapshot import AdminMetricSnapshot

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "admin_metrics:"


class AdminMetricSnapshotService:
    def __init__(self, db: Session, *, cache: CacheBackend | None = None):
        self._db = db
        self._cache = cache or get_cache_backend()
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_refresh(
        self,
        key: str,
        refresh_func: Callable[[], dict[str, Any]],
        ttl_seconds: int | None = None,
        stale_ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Return cached payload or recompute via *refresh_func*.

        The returned dict always contains:

        - ``cached``: ``True`` when the payload was served from cache/DB.
        - ``stale``: ``True`` when served from a stale snapshot while
          another worker is refreshing.
        - ``refreshed_at``: ISO timestamp of the last refresh.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._settings.admin_metrics_cache_ttl_seconds
        stale_ttl = (
            stale_ttl_seconds
            if stale_ttl_seconds is not None
            else self._settings.admin_metrics_stale_ttl_seconds
        )

        cache_key = f"{_CACHE_PREFIX}{key}"

        # 1. Try cache
        cached = self._cache.get_json(cache_key)
        if cached is not None:
            return {**cached, "cached": True, "stale": False}

        # 2. Cache miss — try to acquire lock and refresh
        lock_key = f"admin_metrics:{key}"
        with self._cache.acquire_lock(lock_key, ttl_seconds=ttl) as acquired:
            if acquired:
                return self._do_refresh(cache_key, key, refresh_func, ttl, stale_ttl)

            # 3. Another worker is refreshing — serve stale DB snapshot
            return self._serve_stale(key, refresh_func, ttl, stale_ttl)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _do_refresh(
        self,
        cache_key: str,
        snapshot_key: str,
        refresh_func: Callable[[], dict[str, Any]],
        ttl: int,
        stale_ttl: int,
    ) -> dict[str, Any]:
        from app.models.user import utc_now

        payload = refresh_func()
        now = utc_now()
        meta = {
            "refreshed_at": now.isoformat(),
        }
        full_payload = {**payload, **meta}

        # Write cache
        self._cache.set_json(cache_key, full_payload, ttl_seconds=ttl)

        # Write DB snapshot
        self._write_snapshot(snapshot_key, full_payload, now, ttl + stale_ttl)

        return {**full_payload, "cached": False, "stale": False}

    def _serve_stale(
        self,
        key: str,
        refresh_func: Callable[[], dict[str, Any]],
        ttl: int,
        stale_ttl: int,
    ) -> dict[str, Any]:
        """Return a stale DB snapshot, or compute live as last resort."""
        snapshot = self._read_snapshot(key)
        if snapshot is not None:
            return {**snapshot, "cached": True, "stale": True}

        # No snapshot at all — must compute live
        logger.warning("No snapshot for key=%s, computing live", key)
        payload = refresh_func()
        from app.models.user import utc_now

        meta = {"refreshed_at": utc_now().isoformat()}
        return {**payload, **meta, "cached": False, "stale": False}

    def _write_snapshot(
        self,
        key: str,
        payload: dict[str, Any],
        now: datetime,
        stale_ttl: int,
    ) -> None:
        try:
            existing = (
                self._db.query(AdminMetricSnapshot)
                .filter_by(key=key)
                .one_or_none()
            )
            payload_json = json.dumps(payload, ensure_ascii=False, default=str)
            if existing:
                existing.payload_json = payload_json
                existing.refreshed_at = now
                existing.expires_at = now + timedelta(seconds=stale_ttl)
            else:
                self._db.add(
                    AdminMetricSnapshot(
                        key=key,
                        payload_json=payload_json,
                        refreshed_at=now,
                        expires_at=now + timedelta(seconds=stale_ttl),
                    )
                )
            self._db.commit()
        except Exception as exc:
            logger.warning("Failed to write snapshot key=%s: %s", key, exc)
            self._db.rollback()

    def _read_snapshot(self, key: str) -> dict[str, Any] | None:
        try:
            row = (
                self._db.query(AdminMetricSnapshot)
                .filter_by(key=key)
                .one_or_none()
            )
            if row is None:
                return None
            return json.loads(row.payload_json)
        except Exception as exc:
            logger.warning("Failed to read snapshot key=%s: %s", key, exc)
            return None
