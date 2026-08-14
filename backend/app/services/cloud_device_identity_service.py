"""Stable, encrypted identity for this Zhangshu installation."""

from __future__ import annotations

import platform
import uuid

from sqlalchemy.orm import Session

from app.services.app_config_service import AppConfigService

KEY_CLOUD_DEVICE_ID = "cloud_device_id"
KEY_CLOUD_DEVICE_NAME = "cloud_device_name"


class CloudDeviceIdentityService:
    """Returns a persistent random device id and a human-readable label."""

    def __init__(self, db: Session):
        self._config = AppConfigService(db)

    def get_or_create(self) -> tuple[str, str]:
        device_id = self._config.get_decrypted(KEY_CLOUD_DEVICE_ID)
        device_name = self._config.get_decrypted(KEY_CLOUD_DEVICE_NAME)
        if device_id and device_name:
            return device_id, device_name

        device_id = device_id or str(uuid.uuid4())
        host = (platform.node() or "本机").strip()
        device_name = device_name or f"章枢 · {host}"
        self._config.apply_atomic(
            {
                KEY_CLOUD_DEVICE_ID: device_id,
                KEY_CLOUD_DEVICE_NAME: device_name,
            }
        )
        return device_id, device_name
