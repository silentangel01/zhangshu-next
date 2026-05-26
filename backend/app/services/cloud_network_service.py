"""Service layer for cloud network diagnostics and settings.

Orchestrates diagnostic steps and generates user-readable reports.
Does NOT mix diagnostic logic into login, register, or backup services.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.infrastructure.cloud_api_client import CloudNetworkMode
from app.infrastructure import cloud_network_diagnostics as diag
from app.services.cloud_auth_service import CloudAuthService

logger = logging.getLogger(__name__)


class CloudNetworkService:
    """Manages cloud network diagnostics and connection mode settings."""

    def __init__(self, db: Session):
        self._db = db
        self._auth = CloudAuthService(db)

    # ── Settings ─────────────────────────────────────────────────────

    def get_settings(self) -> dict:
        """Return current network settings summary."""
        mode = self._auth.get_network_mode()
        last_working = self._auth.get_last_working_mode()
        from app.infrastructure.cloud_api_client import CloudApiClient
        client = CloudApiClient()
        return {
            "mode": mode,
            "last_working_mode": last_working,
            "base_url_configured": client.is_configured,
        }

    def set_mode(self, mode: str) -> dict:
        """Update the cloud network mode."""
        from app.infrastructure.cloud_api_client import CloudApiClient

        validated = self._auth.set_network_mode(mode)
        client = CloudApiClient()
        return {
            "mode": validated,
            "last_working_mode": self._auth.get_last_working_mode(),
            "base_url_configured": client.is_configured,
        }

    # ── Diagnostics ──────────────────────────────────────────────────

    def run_diagnostics(self) -> dict:
        """Run all diagnostic steps and produce a report."""
        steps = diag.run_all_diagnostics()

        # Determine overall status and recommended mode
        all_ok = all(s["ok"] for s in steps)
        recommended_mode = self._recommend_mode(steps)

        # Build summary
        if all_ok:
            summary = "云服务连接正常。"
        else:
            failed = [s for s in steps if not s["ok"]]
            first_failure = failed[0] if failed else None
            if first_failure:
                summary = first_failure.get("suggestion") or first_failure.get("message", "连接异常。")
            else:
                summary = "连接异常，请检查诊断详情。"

        return {
            "ok": all_ok,
            "recommended_mode": recommended_mode,
            "summary": summary,
            "steps": steps,
        }


def _recommend_mode(steps: list[dict]) -> CloudNetworkMode:
    """Based on diagnostic results, recommend a connection mode."""
    # Check if secure HTTPS works
    for step in steps:
        if step["name"] == "secure_https_check" and step["ok"]:
            return "secure_direct"

    # Check if system proxy works
    for step in steps:
        if step["name"] == "system_proxy_check" and step["ok"]:
            return "system_proxy"

    # Check if compat mode works
    for step in steps:
        if step["name"] == "compat_no_sni_check" and step["ok"]:
            return "compat_no_sni"

    # Default to auto (let the strategy chain try)
    return "auto"
