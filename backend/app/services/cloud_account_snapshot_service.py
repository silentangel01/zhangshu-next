"""Encrypted local snapshot for instant cloud-account rendering."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services.app_config_service import AppConfigService
from app.services.cloud_auth_service import CloudAuthError, CloudAuthService
from app.services.cloud_device_identity_service import CloudDeviceIdentityService

KEY_CLOUD_ACCOUNT_SNAPSHOT = "cloud_account_snapshot"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CloudAccountSnapshotService:
    """Keeps the last good account payload locally without blocking page entry."""

    def __init__(self, db: Session):
        self._config = AppConfigService(db)
        self._auth = CloudAuthService(db)
        self._device = CloudDeviceIdentityService(db)

    def get_snapshot(self) -> dict:
        status = self._auth.get_account_status()
        raw = self._config.get_decrypted(KEY_CLOUD_ACCOUNT_SNAPSHOT)
        cached: dict = {}
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    cached = parsed
            except (TypeError, ValueError):
                cached = {}

        device_id, device_name = self._device.get_or_create()
        return {
            "status": status,
            "profile": cached.get("profile"),
            "usage": cached.get("usage"),
            "cached_at": cached.get("cached_at"),
            "cache_state": "fresh" if cached else "empty",
            "session_state": "active" if status["logged_in"] else "signed_out",
            "device": {"id": device_id, "name": device_name},
            "refresh_error": None,
        }

    def refresh_snapshot(self) -> dict:
        snapshot = self.get_snapshot()
        if not snapshot["status"]["logged_in"]:
            return snapshot

        try:
            profile = self._auth.get_account_profile()
            usage = self._auth.get_usage()
        except CloudAuthError as exc:
            snapshot["cache_state"] = "stale" if snapshot["profile"] else "empty"
            snapshot["refresh_error"] = str(exc)
            if exc.status_code == 401 or exc.error_kind == "token_expired":
                snapshot["session_state"] = "expired"
            return snapshot

        cached_at = _now_iso()
        self._config.set_value(
            KEY_CLOUD_ACCOUNT_SNAPSHOT,
            json.dumps(
                {"profile": profile, "usage": usage, "cached_at": cached_at},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
        snapshot.update(
            {
                "profile": profile,
                "usage": usage,
                "cached_at": cached_at,
                "cache_state": "fresh",
                "session_state": "active",
                "refresh_error": None,
            }
        )
        return snapshot

    def update_profile(self, profile: dict) -> None:
        snapshot = self.get_snapshot()
        self._config.set_value(
            KEY_CLOUD_ACCOUNT_SNAPSHOT,
            json.dumps(
                {
                    "profile": profile,
                    "usage": snapshot.get("usage"),
                    "cached_at": _now_iso(),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
