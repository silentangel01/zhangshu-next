"""Aliyun service monitoring with in-memory caching.

Aggregates BSS billing, OSS storage, and SWAS server metrics behind
a single ``get_overview()`` call.  Each module is cached independently
with its own TTL so that a slow or failing API does not block the others.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from app.core.config import Settings
from app.infrastructure.aliyun_monitor import (
    AliyunMonitorError,
    BSSMonitor,
    OSSMonitor,
    SWASMonitor,
)

logger = logging.getLogger(__name__)


class _CacheEntry:
    __slots__ = ("data", "error", "_mono", "_wall", "ttl_seconds")

    def __init__(
        self,
        data: dict[str, Any] | None,
        error: str | None,
        ttl_seconds: int,
    ):
        self.data = data
        self.error = error
        self._mono = time.monotonic()
        self._wall = time.time()
        self.ttl_seconds = ttl_seconds

    @property
    def expired(self) -> bool:
        return (time.monotonic() - self._mono) > self.ttl_seconds

    def to_dict(self) -> dict[str, Any]:
        from datetime import datetime, timezone

        ts = datetime.fromtimestamp(self._wall, tz=timezone.utc).isoformat()
        return {
            "data": self.data,
            "error": self.error,
            "cached_at": ts,
            "ttl_seconds": self.ttl_seconds,
        }


class AdminMonitoringService:
    """Aggregates Aliyun service metrics with in-memory caching.

    Cache is stored as a **class variable** so it is shared across all
    instances within the same process.  cloud-server runs as a single
    process, so this is sufficient and avoids Redis/file dependencies.
    """

    _CACHE_TTLS: dict[str, int] = {
        "billing": 3600,  # 1 hour
        "oss": 3600,  # 1 hour
        "server": 300,  # 5 minutes
    }

    _cache: dict[str, _CacheEntry] = {}
    _lock = threading.Lock()

    def __init__(self, settings: Settings):
        self._settings = settings

    # ── public API ──────────────────────────────────────────────────

    def get_overview(self) -> dict[str, Any]:
        """Return all monitoring modules with cache metadata."""
        return {
            "billing": self._cached_call("billing", self._fetch_billing),
            "oss": self._cached_call("oss", self._fetch_oss),
            "server": self._cached_call("server", self._fetch_server),
        }

    def refresh(self, module: str | None = None) -> dict[str, Any]:
        """Force-refresh one module (or all if *module* is ``None``)."""
        with self._lock:
            if module:
                self._cache.pop(module, None)
            else:
                self._cache.clear()
        return self.get_overview()

    # ── cached call wrapper ─────────────────────────────────────────

    def _cached_call(
        self, key: str, fetcher: Callable[[], dict[str, Any]]
    ) -> dict[str, Any]:
        ttl = self._CACHE_TTLS.get(key, 300)

        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.expired:
                return entry.to_dict()

        # Cache miss or expired — call the fetcher outside the lock
        # to avoid blocking other threads on slow API calls.
        try:
            data = fetcher()
            entry = _CacheEntry(
                data=data, error=None, ttl_seconds=ttl
            )
        except AliyunMonitorError as exc:
            logger.warning("Monitoring fetch [%s] failed: %s", key, exc)
            entry = _CacheEntry(
                data=None, error=str(exc), ttl_seconds=ttl
            )
        except Exception as exc:
            logger.exception("Monitoring fetch [%s] unexpected error", key)
            entry = _CacheEntry(
                data=None, error=f"未知错误: {exc}", ttl_seconds=ttl
            )

        with self._lock:
            self._cache[key] = entry

        return entry.to_dict()

    # ── fetchers ────────────────────────────────────────────────────

    def _fetch_billing(self) -> dict[str, Any]:
        s = self._settings
        ak = s.aliyun_monitor_access_key_id or s.oss_access_key_id
        sk = s.aliyun_monitor_access_key_secret or s.oss_access_key_secret
        if not ak or not sk:
            raise AliyunMonitorError("未配置阿里云监控 AccessKey")
        monitor = BSSMonitor(ak, sk)
        return monitor.get_balance()

    def _fetch_oss(self) -> dict[str, Any]:
        s = self._settings
        ak = s.aliyun_monitor_access_key_id or s.oss_access_key_id
        sk = s.aliyun_monitor_access_key_secret or s.oss_access_key_secret
        if not ak or not sk:
            raise AliyunMonitorError("未配置阿里云监控 AccessKey")
        endpoint = s.effective_internal_endpoint or s.effective_public_endpoint
        monitor = OSSMonitor(ak, sk, endpoint, s.oss_bucket_name)
        return monitor.get_bucket_stats()

    def _fetch_server(self) -> dict[str, Any]:
        s = self._settings
        ak = s.aliyun_monitor_access_key_id or s.oss_access_key_id
        sk = s.aliyun_monitor_access_key_secret or s.oss_access_key_secret
        if not ak or not sk:
            raise AliyunMonitorError("未配置阿里云监控 AccessKey")
        if not s.swas_instance_id:
            raise AliyunMonitorError("未配置 SWAS_INSTANCE_ID")
        monitor = SWASMonitor(ak, sk, s.swas_region_id, s.swas_instance_id)
        info = monitor.get_instance_info()
        monitor_data = monitor.get_monitor_data()
        return {"info": info, "monitor": monitor_data}
