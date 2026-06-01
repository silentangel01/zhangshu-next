"""Aliyun service monitors — BSS billing, OSS storage, SWAS server status.

Each monitor class wraps a single Aliyun service API and returns plain dicts.
All exceptions are converted to ``AliyunMonitorError`` for uniform handling
by the service layer.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AliyunMonitorError(Exception):
    """Raised when an Aliyun monitoring API call fails."""


# ── BSS (Billing) ────────────────────────────────────────────────────


class BSSMonitor:
    """Query account balance via BSS OpenAPI."""

    def __init__(self, ak: str, sk: str):
        from alibabacloud_bssopenapi20171214.client import Client as BssClient
        from alibabacloud_tea_openapi.models import Config

        config = Config(
            access_key_id=ak,
            access_key_secret=sk,
            endpoint="business.aliyuncs.com",
        )
        self._client = BssClient(config)

    def get_balance(self) -> dict[str, Any]:
        """Return account balance information.

        Returns dict with keys: available_amount, currency, credit_amount,
        mybank_credit_amount, available_cash_amount.
        """
        try:
            resp = self._client.query_account_balance()
        except Exception as exc:
            raise AliyunMonitorError(f"BSS 查询余额失败: {exc}") from exc

        data = resp.body.data
        if not data:
            raise AliyunMonitorError("BSS 返回空数据")

        return {
            "available_amount": str(data.available_amount or "0"),
            "currency": str(data.currency or "CNY"),
            "credit_amount": str(data.credit_amount or "0"),
            "mybank_credit_amount": str(data.mybank_credit_amount or "0"),
            "available_cash_amount": str(data.available_cash_amount or "0"),
        }


# ── OSS (Object Storage) ─────────────────────────────────────────────


class OSSMonitor:
    """Query bucket storage statistics via oss2."""

    def __init__(self, ak: str, sk: str, endpoint: str, bucket_name: str):
        import oss2

        auth = oss2.Auth(ak, sk)
        self._bucket = oss2.Bucket(auth, endpoint, bucket_name)
        self._bucket_name = bucket_name

    def get_bucket_stats(self) -> dict[str, Any]:
        """Return bucket storage statistics.

        Returns dict with keys: storage_bytes, object_count,
        standard_storage, ia_storage, archive_storage, bucket_name.
        """
        try:
            result = self._bucket.get_bucket_stat()
        except Exception as exc:
            raise AliyunMonitorError(
                f"OSS GetBucketStat 失败: {exc}"
            ) from exc

        return {
            "storage_bytes": int(result.storage_size_in_bytes),
            "object_count": int(result.object_count),
            "standard_storage": int(
                getattr(result, "standard_storage", 0) or 0
            ),
            "ia_storage": int(
                getattr(result, "infrequent_access_storage", 0) or 0
            ),
            "archive_storage": int(
                getattr(result, "archive_storage", 0) or 0
            ),
            "bucket_name": self._bucket_name,
        }


# ── SWAS (轻量应用服务器) ────────────────────────────────────────────


class SWASMonitor:
    """Query lightweight application server info and monitoring data.

    Instance info comes from the SWAS API.  Monitoring metrics come from
    CloudMonitor (CMS) because the SWAS DescribeMonitorData endpoint is
    unreliable (frequent 500 errors on newer instances).
    """

    # CMS metric name → result key
    _CMS_METRICS: dict[str, str] = {
        "cpu_total": "cpu_usage",
        "memory_utilization": "memory_usage",
        "DiskReadIOPS": "disk_read_iops",
        "DiskWriteIOPS": "disk_write_iops",
        "networkin_rate": "net_rx_bps",
        "networkout_rate": "net_tx_bps",
    }

    def __init__(
        self, ak: str, sk: str, region_id: str, instance_id: str
    ):
        from alibabacloud_swas_open20200601.client import Client as SwasClient
        from alibabacloud_tea_openapi.models import Config

        config = Config(
            access_key_id=ak,
            access_key_secret=sk,
            endpoint=f"swas.{region_id}.aliyuncs.com",
        )
        self._swas = SwasClient(config)
        self._region_id = region_id
        self._instance_id = instance_id
        self._ak = ak
        self._sk = sk

    # ── instance info (SWAS API) ────────────────────────────────────

    def get_instance_info(self) -> dict[str, Any]:
        """Return basic instance information."""
        from alibabacloud_swas_open20200601 import models as swas_models

        try:
            req = swas_models.ListInstancesRequest(
                region_id=self._region_id,
                instance_ids='["' + self._instance_id + '"]',
            )
            resp = self._swas.list_instances(req)
        except Exception as exc:
            raise AliyunMonitorError(
                f"SWAS ListInstances 失败: {exc}"
            ) from exc

        instances = resp.body.instances or []
        if not instances:
            raise AliyunMonitorError(
                f"SWAS 实例 {self._instance_id} 未找到"
            )

        inst = instances[0]
        spec = self._format_spec(inst)

        return {
            "name": inst.instance_name or "",
            "status": inst.status or "Unknown",
            "public_ip": inst.public_ip_address or "",
            "spec": spec,
            "os_name": (inst.image.image_name if inst.image else "") or "",
            "created_at": inst.creation_time or "",
            "expired_at": inst.expired_time or "",
            "region_id": self._region_id,
            "charge_type": inst.charge_type or "",
        }

    # ── monitoring data (CMS API) ───────────────────────────────────

    def get_monitor_data(self) -> dict[str, Any]:
        """Return latest monitoring metrics via CloudMonitor.

        Returns dict with keys: cpu_usage, memory_usage, disk_read_iops,
        disk_write_iops, net_rx_bps, net_tx_bps, timestamp, available.

        ``available`` is False when no monitoring data exists yet (e.g.
        brand-new instances).
        """
        from alibabacloud_cms20190101.client import Client as CmsClient
        from alibabacloud_cms20190101 import models as cms_models
        from alibabacloud_tea_openapi.models import Config
        from datetime import datetime, timezone

        cms_config = Config(
            access_key_id=self._ak,
            access_key_secret=self._sk,
            endpoint="metrics.aliyuncs.com",
        )
        cms = CmsClient(cms_config)

        now = datetime.now(timezone.utc)
        result: dict[str, Any] = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_read_iops": 0.0,
            "disk_write_iops": 0.0,
            "net_rx_bps": 0.0,
            "net_tx_bps": 0.0,
            "timestamp": now.isoformat(),
            "available": False,
        }

        dimensions = json.dumps(
            [{"instanceId": self._instance_id}]
        )

        for cms_metric, result_key in self._CMS_METRICS.items():
            try:
                req = cms_models.DescribeMetricLastRequest(
                    namespace="acs_swas",
                    metric_name=cms_metric,
                    dimensions=dimensions,
                )
                resp = cms.describe_metric_last(req)
                raw = resp.body.datapoints
                if not raw:
                    continue
                points = json.loads(raw)
                if points:
                    latest = points[-1] if isinstance(points, list) else points
                    avg = latest.get("Average", latest.get("average", 0))
                    result[result_key] = float(avg or 0)
                    result["available"] = True
                    ts = latest.get("timestamp")
                    if ts and result_key == "cpu_usage":
                        result["timestamp"] = datetime.fromtimestamp(
                            int(ts) / 1000, tz=timezone.utc
                        ).isoformat()
            except Exception as exc:
                logger.warning(
                    "CMS metric %s failed: %s", cms_metric, exc
                )

        return result

    @staticmethod
    def _format_spec(inst: Any) -> str:
        """Format resource spec into human-readable string."""
        spec = getattr(inst, "resource_spec", None)
        if not spec:
            return ""
        cpu = getattr(spec, "cpu", 0) or 0
        mem = getattr(spec, "memory", 0) or 0
        disk = getattr(spec, "disk_size", 0) or 0
        bw = getattr(spec, "bandwidth", 0) or 0
        parts = []
        if cpu:
            parts.append(f"{cpu} vCPU")
        if mem:
            parts.append(f"{mem:.0f} GB")
        if disk:
            parts.append(f"{disk} GB {getattr(spec, 'disk_category', '') or ''}".strip())
        if bw:
            parts.append(f"{bw} Mbps")
        return " / ".join(parts)
