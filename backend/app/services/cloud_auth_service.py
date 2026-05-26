"""Service layer for cloud account authentication and token management."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.infrastructure.cloud_api_client import (
    CloudApiClient,
    CloudApiError,
    CloudApiNotConfiguredError,
    CloudNetworkMode,
)
from app.services.app_config_service import AppConfigService

logger = logging.getLogger(__name__)

# Config keys for cloud auth tokens (auto-encrypted via SENSITIVE_KEYS)
_KEY_ACCESS_TOKEN = "cloud_access_token"
_KEY_REFRESH_TOKEN = "cloud_refresh_token"
_KEY_USER_ID = "cloud_user_id"
_KEY_USER_EMAIL = "cloud_user_email"

# Valid modes — used to validate user input
_VALID_MODES = {"auto", "secure_direct", "system_proxy", "compat_no_sni"}


class CloudAuthError(Exception):
    """Raised when cloud authentication fails."""

    def __init__(
        self,
        message: str,
        error_kind: str = "",
        suggestion: str = "",
    ):
        super().__init__(message)
        self.error_kind = error_kind
        self.suggestion = suggestion


class CloudAuthService:
    """Manages cloud account login / logout / token storage."""

    def __init__(self, db: Session):
        self._db = db
        self._config = AppConfigService(db)

    # ── Public API ────────────────────────────────────────────────

    def get_account_status(self) -> dict:
        """Always returns 200. ``logged_in`` reflects whether we have a token."""
        client = self._build_client()
        cloud_available = client.is_configured

        access_token = self._config.get_decrypted(_KEY_ACCESS_TOKEN)
        email = self._config.get_decrypted(_KEY_USER_EMAIL)

        if not access_token:
            return {
                "logged_in": False,
                "cloud_available": cloud_available,
                "email": None,
                "display_name": None,
            }

        return {
            "logged_in": True,
            "cloud_available": cloud_available,
            "email": email,
            "display_name": email,
        }

    def get_api_client(self) -> CloudApiClient:
        """Build a CloudApiClient with the stored access token and network mode."""
        return self._build_client()

    def is_logged_in(self) -> bool:
        token = self._config.get_decrypted(_KEY_ACCESS_TOKEN)
        return bool(token)

    def login(self, email: str, password: str) -> dict:
        client = self._build_client()
        try:
            result = client.login(email, password)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
            ) from exc

        self._store_tokens(result, email)
        return {
            "logged_in": True,
            "cloud_available": True,
            "email": email,
            "display_name": email,
        }

    def register(self, email: str, password: str, display_name: str) -> dict:
        client = self._build_client()
        try:
            result = client.register(email, password, display_name)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
            ) from exc

        self._store_tokens(result, email)
        return {
            "logged_in": True,
            "cloud_available": True,
            "email": email,
            "display_name": display_name or email,
        }

    def logout(self) -> None:
        for key in (
            _KEY_ACCESS_TOKEN,
            _KEY_REFRESH_TOKEN,
            _KEY_USER_ID,
            _KEY_USER_EMAIL,
        ):
            self._config.delete_value(key)

    # ── Internal ──────────────────────────────────────────────────

    def _build_client(self) -> CloudApiClient:
        """Build a CloudApiClient with stored token and network mode."""
        access_token = self._config.get_decrypted(_KEY_ACCESS_TOKEN) or ""
        mode = self.get_network_mode()
        return CloudApiClient(access_token=access_token, mode=mode)

    def _store_tokens(self, auth_payload: dict, email: str) -> None:
        self._config.set_value(
            _KEY_ACCESS_TOKEN, str(auth_payload.get("access_token", ""))
        )
        self._config.set_value(
            _KEY_REFRESH_TOKEN, str(auth_payload.get("refresh_token", ""))
        )
        self._config.set_value(
            _KEY_USER_ID, str(auth_payload.get("user_id", ""))
        )
        self._config.set_value(_KEY_USER_EMAIL, email)

    def get_cloud_user_id(self) -> str:
        """Return the current cloud user's ID, or empty string if not logged in."""
        return self._config.get_decrypted(_KEY_USER_ID) or ""

    # ── Network mode ──────────────────────────────────────────────

    def get_network_mode(self) -> CloudNetworkMode:
        """Return the configured network mode, defaulting to 'auto'."""
        stored = self._config.get_value("cloud_network_mode")
        if stored and stored in _VALID_MODES:
            return stored  # type: ignore[return-value]
        return "auto"

    def set_network_mode(self, mode: str) -> CloudNetworkMode:
        """Save the network mode. Validates against known modes."""
        if mode not in _VALID_MODES:
            raise ValueError(f"无效的连接模式: {mode}。可选: {', '.join(sorted(_VALID_MODES))}")
        self._config.set_value("cloud_network_mode", mode)
        return mode  # type: ignore[return-value]

    def get_last_working_mode(self) -> str | None:
        """Return the last auto-detected working mode, if any."""
        return self._config.get_value("cloud_last_working_mode")

    def set_last_working_mode(self, mode: str) -> None:
        """Save the last working mode detected by auto strategy."""
        if mode in _VALID_MODES:
            self._config.set_value("cloud_last_working_mode", mode)
