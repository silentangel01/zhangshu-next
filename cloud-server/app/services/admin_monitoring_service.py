"""Aliyun service monitoring with shared cache backend.

Aggregates BSS billing, OSS storage, and SWAS server metrics behind
a single ``get_overview()`` call.  Each module is cached independently
with its own TTL so that a slow or failing API does not block the others.

Cache is stored via :class:`~app.core.cache.CacheBackend` — shared
across workers in production (Redis) and per-process in development
(memory).  This replaces the previous class-variable ``_cache`` which
only worked within a single process.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import Settings
from app.infrastructure.aliyun_monitor import (
    AliyunMonitorError,
    BSSMonitor,
    OSSMonitor,
    SWASMonitor,
)

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "monitoring:"


class AdminMonitoringService:
    """Aggregates Aliyun service metrics with shared cache backend."""

    _CACHE_TTLS: dict[str, int] = {
        "billing": 3600,  # 1 hour
        "oss": 3600,  # 1 hour
        "server": 300,  # 5 minutes
    }

    def __init__(
        self,
        settings: Settings,
        *,
        cache: CacheBackend | None = None,
    ):
        self._settings = settings
        self._cache = cache or get_cache_backend()

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
        if module:
            self._cache.delete(f"{_CACHE_PREFIX}{module}")
        else:
            for key in self._CACHE_TTLS:
                self._cache.delete(f"{_CACHE_PREFIX}{key}")
        return self.get_overview()

    # ── cached call wrapper ─────────────────────────────────────────

    def _cached_call(
        self, key: str, fetcher: Callable[[], dict[str, Any]]
    ) -> dict[str, Any]:
        ttl = self._CACHE_TTLS.get(key, 300)
        cache_key = f"{_CACHE_PREFIX}{key}"

        # Try cache first
        cached = self._cache.get_json(cache_key)
        if cached is not None:
            return cached

        # Cache miss — call the fetcher
        try:
            data = fetcher()
            entry = self._make_entry(data=data, error=None, ttl_seconds=ttl)
        except AliyunMonitorError as exc:
            logger.warning("Monitoring fetch [%s] failed: %s", key, exc)
            entry = self._make_entry(data=None, error=str(exc), ttl_seconds=ttl)
        except Exception as exc:
            logger.exception("Monitoring fetch [%s] unexpected error", key)
            entry = self._make_entry(
                data=None, error=f"未知错误: {exc}", ttl_seconds=ttl
            )

        self._cache.set_json(cache_key, entry, ttl_seconds=ttl)
        return entry

    @staticmethod
    def _make_entry(
        *,
        data: dict[str, Any] | None,
        error: str | None,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        ts = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        return {
            "data": data,
            "error": error,
            "cached_at": ts,
            "ttl_seconds": ttl_seconds,
        }

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
