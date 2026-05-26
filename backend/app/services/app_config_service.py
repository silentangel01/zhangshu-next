"""Service layer for app configuration with transparent encryption."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.infrastructure.config_crypto import (
    decrypt_value,
    encrypt_value,
    is_sensitive,
)
from app.repositories.app_config_repo import AppConfigRepository

logger = logging.getLogger(__name__)

# Well-known config keys
KEY_DASHSCOPE_API_KEY = "dashscope_api_key"
KEY_LLM_ENABLED = "llm_enabled"
KEY_LLM_MODEL = "llm_model"
KEY_LLM_BASE_URL = "llm_base_url"
KEY_LLM_PROVIDER = "llm_provider"

# Cloud network resilience keys (non-sensitive, stored in plaintext)
KEY_CLOUD_NETWORK_MODE = "cloud_network_mode"
KEY_CLOUD_LAST_WORKING_MODE = "cloud_last_working_mode"


class AppConfigService:
    """Manages app configuration with transparent encryption."""

    def __init__(self, db: Session):
        self._repo = AppConfigRepository(db)

    def get_all_masked(self) -> dict[str, object]:
        """Return all config. Sensitive values are returned masked.

        Non-sensitive: ``{"some_key": "plain_value"}``
        Sensitive: ``{"dashscope_api_key": {"has_value": True, "masked": "****abcd"}}``
        Decrypt error: adds ``"decrypt_error": True`` to the dict.
        """
        result: dict[str, object] = {}
        for entry in self._repo.get_all():
            if entry.is_encrypted:
                try:
                    plaintext = decrypt_value(entry.config_value)
                except Exception:
                    logger.warning(
                        "Failed to decrypt config key '%s'.",
                        entry.config_key,
                    )
                    result[entry.config_key] = {
                        "has_value": True,
                        "masked": "****????",
                        "decrypt_error": True,
                    }
                    continue
                masked = (
                    "****" + plaintext[-4:] if len(plaintext) > 4 else "****"
                )
                result[entry.config_key] = {
                    "has_value": True,
                    "masked": masked,
                }
            else:
                result[entry.config_key] = entry.config_value
        return result

    def get_value(self, key: str) -> str | None:
        """Return the raw value for a key, or None.

        For encrypted keys, returns the encrypted ciphertext (not decrypted).
        Use get_decrypted() for sensitive keys.
        """
        entry = self._repo.get(key)
        if entry is None:
            return None
        return entry.config_value

    def get_decrypted(self, key: str) -> str | None:
        """Return decrypted value for a key, or None."""
        entry = self._repo.get(key)
        if entry is None:
            return None
        if entry.is_encrypted:
            try:
                return decrypt_value(entry.config_value)
            except Exception:
                logger.warning("Failed to decrypt config key '%s'.", key)
                return None
        return entry.config_value

    def set_value(self, key: str, value: str) -> None:
        """Set a config value, encrypting if the key is sensitive."""
        if is_sensitive(key):
            encrypted = encrypt_value(value)
            self._repo.upsert(key, encrypted, is_encrypted=True)
        else:
            self._repo.upsert(key, value, is_encrypted=False)

    def delete_value(self, key: str) -> bool:
        """Delete a config entry."""
        return self._repo.delete(key)
