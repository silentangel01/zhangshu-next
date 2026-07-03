"""Service layer for cloud account authentication and token management."""

from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

from sqlalchemy.orm import Session

from app.infrastructure.cloud_api_client import (
    CloudApiClient,
    CloudApiError,
    CloudApiNotConfiguredError,
    CloudNetworkMode,
)
from app.services.app_config_service import AppConfigService

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Config keys for cloud auth tokens (auto-encrypted via SENSITIVE_KEYS)
_KEY_ACCESS_TOKEN = "cloud_access_token"
_KEY_REFRESH_TOKEN = "cloud_refresh_token"
_KEY_USER_ID = "cloud_user_id"
_KEY_USER_EMAIL = "cloud_user_email"
_KEY_USER_PHONE = "cloud_user_phone"
_KEY_USER_OAUTH_LABEL = "cloud_user_oauth_label"

# Valid modes — used to validate user input
_VALID_MODES = {"auto", "secure_direct", "system_proxy", "compat_no_sni"}


class CloudAuthError(Exception):
    """Raised when cloud authentication fails."""

    def __init__(
        self,
        message: str,
        error_kind: str = "",
        suggestion: str = "",
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.error_kind = error_kind
        self.suggestion = suggestion
        self.status_code = status_code


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
        phone = self._config.get_decrypted(_KEY_USER_PHONE)
        oauth_label = self._config.get_decrypted(_KEY_USER_OAUTH_LABEL)

        if not access_token:
            return {
                "logged_in": False,
                "cloud_available": cloud_available,
                "email": None,
                "display_name": None,
                "phone_number": None,
                "token_expired": False,
            }

        return {
            "logged_in": True,
            "cloud_available": cloud_available,
            "email": email,
            "display_name": email or phone or oauth_label,
            "phone_number": phone,
            "token_expired": False,
        }

    def get_api_client(self) -> CloudApiClient:
        """Build a CloudApiClient with the stored access token and network mode."""
        return self._build_client()

    def call_with_refresh(self, fn: Callable[[CloudApiClient], T]) -> T:
        """Execute a cloud API call with transparent token refresh on 401.

        Public interface — use this from other service classes that hold a
        reference to ``CloudAuthService``.
        """
        return self._cloud_call(fn)

    def is_logged_in(self) -> bool:
        token = self._config.get_decrypted(_KEY_ACCESS_TOKEN)
        return bool(token)

    def refresh_token(self) -> dict:
        """Public method to manually refresh the access token.

        Returns:
            dict: {"refreshed": True} on success, {"refreshed": False} on failure
        """
        success = self._try_refresh_token()
        return {"refreshed": success}

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
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        self._store_tokens(result, email=email)
        return {
            "logged_in": True,
            "cloud_available": True,
            "email": email,
            "display_name": email,
            "phone_number": None,
        }

    def login_with_email_code(self, email: str, verification_code: str) -> dict:
        client = self._build_client()
        try:
            result = client.login_with_email_code(email, verification_code)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        self._store_tokens(result, email=email)
        return {
            "logged_in": True,
            "cloud_available": True,
            "email": email,
            "display_name": email,
            "phone_number": None,
        }

    def login_with_phone_code(self, phone_number: str, verification_code: str) -> dict:
        client = self._build_client()
        try:
            result = client.login_with_phone_code(phone_number, verification_code)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        self._store_tokens(result, phone_number=phone_number)
        return {
            "logged_in": True,
            "cloud_available": True,
            "email": None,
            "display_name": phone_number,
            "phone_number": phone_number,
        }

    def check_email_available(self, email: str) -> dict:
        client = self._build_client()
        try:
            result = client.check_email(email)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        return result

    def check_phone_available(self, phone_number: str) -> dict:
        client = self._build_client()
        try:
            result = client.check_phone(phone_number)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        return result

    def send_email_code(self, email: str, purpose: str) -> dict:
        client = self._build_client()
        try:
            result = client.send_email_code(email, purpose)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        return result

    def send_phone_code(self, phone_number: str, purpose: str) -> dict:
        client = self._build_client()
        try:
            result = client.send_phone_code(phone_number, purpose)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        return result

    def register(
        self,
        email: str,
        password: str,
        display_name: str,
        verification_code: str,
    ) -> dict:
        client = self._build_client()
        try:
            result = client.register(email, password, display_name, verification_code)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        self._store_tokens(result, email=email)
        return {
            "logged_in": True,
            "cloud_available": True,
            "email": email,
            "display_name": display_name or email,
            "phone_number": None,
        }

    def register_with_phone(
        self,
        phone_number: str,
        verification_code: str,
        display_name: str,
    ) -> dict:
        client = self._build_client()
        try:
            result = client.register_with_phone(
                phone_number, verification_code, display_name
            )
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        self._store_tokens(result, phone_number=phone_number)
        return {
            "logged_in": True,
            "cloud_available": True,
            "email": None,
            "display_name": display_name or phone_number,
            "phone_number": phone_number,
        }

    def start_oauth_login(self, provider: str) -> dict:
        client = self._build_client()
        try:
            result = client.start_oauth_login(provider)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        return result

    def poll_oauth_login(self, session_id: str, poll_token: str) -> dict:
        client = self._build_client()
        try:
            result = client.poll_oauth_login(session_id, poll_token)
        except CloudApiNotConfiguredError:
            raise
        except CloudApiError as exc:
            raise CloudAuthError(
                str(exc),
                error_kind=exc.error_kind,
                suggestion=exc.suggestion,
                status_code=exc.status_code,
            ) from exc

        self._record_working_mode(client)
        if result.get("status") != "completed":
            return result

        display_name = str(result.get("display_name") or result.get("provider") or "第三方账号")
        self._store_tokens(result, oauth_label=display_name)
        return {
            "status": "completed",
            "logged_in": True,
            "cloud_available": True,
            "email": None,
            "display_name": display_name,
            "phone_number": None,
        }

    def logout(self) -> None:
        for key in (
            _KEY_ACCESS_TOKEN,
            _KEY_REFRESH_TOKEN,
            _KEY_USER_ID,
            _KEY_USER_EMAIL,
            _KEY_USER_PHONE,
            _KEY_USER_OAUTH_LABEL,
        ):
            self._config.delete_value(key)

    # ── Internal ──────────────────────────────────────────────────

    def _build_client(self) -> CloudApiClient:
        """Build a CloudApiClient with stored token and network mode."""
        access_token = self._config.get_decrypted(_KEY_ACCESS_TOKEN) or ""
        mode = self.get_network_mode()
        preferred = self.get_last_working_mode()
        return CloudApiClient(
            access_token=access_token, mode=mode, preferred_mode=preferred
        )

    def _try_refresh_token(self) -> bool:
        """Attempt to refresh the access token using the stored refresh token.

        Returns True if refresh succeeded, False otherwise.
        On success, new tokens are persisted via ``_store_tokens``.
        """
        refresh_token = self._config.get_decrypted(_KEY_REFRESH_TOKEN)
        if not refresh_token:
            logger.warning("No refresh token available; cannot refresh access token.")
            return False

        mode = self.get_network_mode()
        preferred = self.get_last_working_mode()
        # Build a client WITHOUT the (expired) access token — refresh endpoint
        # authenticates via the refresh_token in the request body, not the header.
        client = CloudApiClient(access_token="", mode=mode, preferred_mode=preferred)
        try:
            result = client.refresh(refresh_token)
        except CloudApiError as exc:
            logger.warning(
                "Token refresh failed (status=%s): %s", exc.status_code, exc
            )
            return False
        except CloudApiNotConfiguredError:
            return False

        email = self._config.get_decrypted(_KEY_USER_EMAIL) or ""
        phone = self._config.get_decrypted(_KEY_USER_PHONE) or ""
        oauth_label = self._config.get_decrypted(_KEY_USER_OAUTH_LABEL) or ""
        self._store_tokens(
            result,
            email=email or None,
            phone_number=phone or None,
            oauth_label=oauth_label or None,
        )
        logger.info("Access token refreshed successfully.")
        return True

    def _record_working_mode(self, client: CloudApiClient) -> None:
        """Cache the connection strategy that succeeded, for faster future calls."""
        mode = client.last_working_mode
        if mode:
            self.set_last_working_mode(mode)

    def _cloud_call(self, fn: Callable[[CloudApiClient], T]) -> T:
        """Execute a cloud API call with transparent token refresh on 401."""
        client = self._build_client()
        try:
            result = fn(client)
            self._record_working_mode(client)
            return result
        except CloudApiError as exc:
            if exc.status_code != 401:
                raise CloudAuthError(
                    str(exc),
                    error_kind=exc.error_kind,
                    suggestion=exc.suggestion,
                    status_code=exc.status_code,
                ) from exc

            # 401 — attempt transparent refresh
            if not self._try_refresh_token():
                raise CloudAuthError(
                    "登录已过期，请重新登录。",
                    error_kind="token_expired",
                    suggestion="请在个人账户页面重新登录。",
                ) from exc

            # Retry with new token
            new_client = self._build_client()
            try:
                result = fn(new_client)
                self._record_working_mode(new_client)
                return result
            except CloudApiError as retry_exc:
                raise CloudAuthError(
                    str(retry_exc),
                    error_kind=retry_exc.error_kind,
                    suggestion=retry_exc.suggestion,
                    status_code=retry_exc.status_code,
                ) from retry_exc

    def _store_tokens(
        self,
        auth_payload: dict,
        *,
        email: str | None = None,
        phone_number: str | None = None,
        oauth_label: str | None = None,
    ) -> None:
        self._config.set_value(
            _KEY_ACCESS_TOKEN, str(auth_payload.get("access_token", ""))
        )
        self._config.set_value(
            _KEY_REFRESH_TOKEN, str(auth_payload.get("refresh_token", ""))
        )
        self._config.set_value(
            _KEY_USER_ID, str(auth_payload.get("user_id", ""))
        )
        if email is not None:
            self._config.set_value(_KEY_USER_EMAIL, email)
            self._config.delete_value(_KEY_USER_PHONE)
            self._config.delete_value(_KEY_USER_OAUTH_LABEL)
        if phone_number is not None:
            self._config.set_value(_KEY_USER_PHONE, phone_number)
            self._config.delete_value(_KEY_USER_EMAIL)
            self._config.delete_value(_KEY_USER_OAUTH_LABEL)
        if oauth_label is not None:
            self._config.set_value(_KEY_USER_OAUTH_LABEL, oauth_label)
            self._config.delete_value(_KEY_USER_EMAIL)
            self._config.delete_value(_KEY_USER_PHONE)

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

    # ── Account management ────────────────────────────────────────

    def get_account_profile(self) -> dict:
        """Fetch the logged-in user's profile from the cloud server."""
        return self._cloud_call(lambda client: client.get_account_profile())

    def update_account_profile(
        self,
        display_name: str | None = None,
        signature: str | None = None,
    ) -> dict:
        """Update the user's display name and/or signature on the cloud server."""
        return self._cloud_call(
            lambda client: client.update_account_profile(
                display_name=display_name, signature=signature
            )
        )

    def send_bind_email_code(self, email: str) -> dict:
        return self._cloud_call(lambda client: client.send_bind_email_code(email))

    def send_bind_phone_code(self, phone_number: str) -> dict:
        return self._cloud_call(lambda client: client.send_bind_phone_code(phone_number))

    def bind_email(self, email: str, verification_code: str) -> dict:
        result = self._cloud_call(
            lambda client: client.bind_email(email, verification_code)
        )
        self._config.set_value(_KEY_USER_EMAIL, email)
        return result

    def bind_phone(self, phone_number: str, verification_code: str) -> dict:
        result = self._cloud_call(
            lambda client: client.bind_phone(phone_number, verification_code)
        )
        self._config.set_value(_KEY_USER_PHONE, phone_number)
        return result

    def change_password(self, old_password: str, new_password: str) -> dict:
        """Change the user's password on the cloud server."""
        return self._cloud_call(
            lambda client: client.change_password(old_password, new_password)
        )

    def revoke_all_sessions(self) -> dict:
        """Revoke all active sessions for the user on the cloud server."""
        return self._cloud_call(lambda client: client.revoke_all_sessions())

    def get_usage(self) -> dict:
        """Fetch the user's storage and backup usage from the cloud server."""
        return self._cloud_call(lambda client: client.get_usage())

    def export_account_data(self) -> dict:
        """Export the user's account data from the cloud server."""
        return self._cloud_call(lambda client: client.export_account_data())

    def request_account_deletion(self, password: str) -> dict:
        """Request account deletion (stage 1: password verification)."""
        return self._cloud_call(
            lambda client: client.request_account_deletion(password)
        )

    def confirm_account_deletion(
        self, request_id: str, confirmation_text: str
    ) -> dict:
        """Confirm account deletion (stage 2: token + confirmation text)."""
        return self._cloud_call(
            lambda client: client.confirm_account_deletion(request_id, confirmation_text)
        )

    # ── Avatar management ─────────────────────────────────────────

    def init_avatar_upload(
        self, filename: str, content_type: str, size_bytes: int
    ) -> dict:
        """Initialize an avatar upload on the cloud server."""
        return self._cloud_call(
            lambda client: client.init_avatar_upload(filename, content_type, size_bytes)
        )

    def upload_avatar_to_oss(
        self, upload_url: str, content: bytes, content_type: str
    ) -> None:
        """Upload avatar bytes directly to OSS via presigned URL."""
        self._cloud_call(
            lambda client: client.upload_avatar(upload_url, content, content_type)
        )

    def complete_avatar_upload(
        self,
        upload_id: str,
        object_key: str,
        content_type: str,
        checksum_sha256: str,
    ) -> dict:
        """Confirm avatar upload completion on the cloud server."""
        return self._cloud_call(
            lambda client: client.complete_avatar_upload(
                upload_id, object_key, content_type, checksum_sha256
            )
        )

    def delete_avatar(self) -> dict | None:
        """Delete the user's avatar on the cloud server."""
        return self._cloud_call(lambda client: client.delete_avatar())
