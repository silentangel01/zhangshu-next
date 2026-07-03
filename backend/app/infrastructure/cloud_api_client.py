"""HTTP client for the remote Zhangshu Cloud API.

Supports multiple connection strategies to handle diverse network environments:
- ``secure_direct``: Full TLS verification, no system proxy.
- ``system_proxy``: Full TLS verification, reads system proxy env vars.
- ``compat_no_sni``: IP direct-connect + Host header, skips SNI/cert verification.
  Used as a fallback for campus/corporate networks with DPI-based SNI filtering.
- ``auto``: Tries secure_direct → system_proxy → compat_no_sni based on errors.

All methods raise ``CloudApiNotConfiguredError`` when the base URL is empty.
"""

from __future__ import annotations

import logging
import os
import socket
import ssl
from typing import Any, Literal
from urllib.parse import urlencode, urlparse

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0
_AUTO_TIMEOUT = 8.0  # Shorter timeout per strategy in auto mode

# Connection mode type — used in config storage and API responses
CloudNetworkMode = Literal["auto", "secure_direct", "system_proxy", "compat_no_sni"]

# Local addresses exempt from HTTPS requirement
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


# ── Error types ──────────────────────────────────────────────────────


class CloudApiNotConfiguredError(Exception):
    """Raised when the Zhangshu Cloud API base URL is not configured."""


class CloudApiError(Exception):
    """Raised when the Zhangshu Cloud API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_kind: str = "",
        suggestion: str = "",
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_kind = error_kind
        self.suggestion = suggestion


# ── SSL / DNS helpers ────────────────────────────────────────────────


def _resolve_ip(hostname: str) -> str:
    """Resolve a hostname to its first IPv4 address."""
    try:
        return socket.getaddrinfo(hostname, 443, socket.AF_INET)[0][4][0]
    except Exception:
        return hostname


def _build_no_sni_context() -> ssl.SSLContext:
    """Build an SSL context that skips SNI and hostname verification.

    This is a **compatibility fallback** for networks with DPI-based SNI
    filtering (e.g. campus/corporate networks). It disables certificate
    verification and should NOT be used as the default connection mode.
    """
    ctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    return ctx


# ── Error classification ─────────────────────────────────────────────


def _classify_error(exc: Exception) -> tuple[str, str]:
    """Classify an httpx/network error into (error_kind, suggestion).

    Returns a tuple of machine-readable kind and user-facing suggestion.
    Does NOT include sensitive information (tokens, URLs, passwords).
    """
    exc_str = str(exc)

    if isinstance(exc, httpx.TimeoutException):
        return (
            "timeout",
            "连接超时，请检查网络或云服务地址是否正确。",
        )

    if isinstance(exc, httpx.ConnectError):
        lower = exc_str.lower()
        if "10054" in exc_str or "reset" in lower or "forcibly" in lower:
            return (
                "tls_reset_or_sni_filtered",
                "连接被重置，可能被校园/公司网络拦截。可尝试兼容模式或系统代理。",
            )
        if "name resolution" in lower or "getaddrinfo" in lower or "dns" in lower:
            return ("dns_failed", "DNS 解析失败，请检查云服务地址是否正确。")
        if "proxy" in lower:
            return (
                "proxy_required_or_interfered",
                "代理连接异常，请检查代理设置或切换连接模式。",
            )
        return ("tcp_unreachable", "无法连接到云服务，请检查地址和网络。")

    if isinstance(exc, (httpx.ConnectTimeout,)):
        return ("timeout", "连接超时，请检查网络或云服务地址。")

    if isinstance(exc, ssl.SSLError):
        return (
            "tls_failed",
            "TLS 握手失败，可尝试兼容模式或检查证书配置。",
        )

    return ("cloud_unavailable", "云服务暂时不可达，请稍后重试。")


def _safe_str(value: object) -> str:
    """Return the string only when *value* is already a non-empty string.

    Returns ``""`` for ``None``, dicts, lists, ints, etc. so that no Python
    repr (``"None"``, ``"{...}"``) leaks into user-visible error messages.
    """
    if isinstance(value, str) and value.strip():
        return value
    return ""


def _parse_remote_error(response: httpx.Response) -> tuple[str, str, str]:
    """Extract a user-readable message from a remote cloud API error body.

    Supports multiple error body formats used by the remote cloud server:
    - ``{"detail": "string error"}``
    - ``{"detail": {"message": "...", "error_kind": "...", "suggestion": "..."}}``
    - ``{"message": "..."}``
    - ``{"error": "..."}``

    Returns ``(message, error_kind, suggestion)`` — empty strings for missing
    fields.  Never includes full URLs, tokens, or passwords.
    """
    message = ""
    error_kind = ""
    suggestion = ""

    try:
        payload = response.json()
    except Exception:
        return (
            f"云服务返回错误 ({response.status_code})",
            "http_status_error",
            "",
        )

    if not isinstance(payload, dict):
        return (
            f"云服务返回错误 ({response.status_code})",
            "http_status_error",
            "",
        )

    detail = payload.get("detail")

    if isinstance(detail, str) and detail.strip():
        message = detail
    elif isinstance(detail, dict):
        message = _safe_str(detail.get("message"))
        error_kind = _safe_str(detail.get("error_kind"))
        suggestion = _safe_str(detail.get("suggestion"))

    # Fallback to top-level keys if detail didn't yield a message
    if not message:
        message = _safe_str(payload.get("message"))
    if not message:
        message = _safe_str(payload.get("error"))
    if not message:
        message = f"云服务返回错误 ({response.status_code})"

    # Top-level suggestion/error_kind as fallback
    if not error_kind and isinstance(payload.get("error_kind"), str):
        error_kind = payload["error_kind"]
    if not suggestion and isinstance(payload.get("suggestion"), str):
        suggestion = payload["suggestion"]

    return (message, error_kind, suggestion)


# ── URL security ─────────────────────────────────────────────────────


def _is_local_url(parsed) -> bool:
    """Check if a parsed URL points to a local development address."""
    hostname = (parsed.hostname or "").lower()
    # Strip brackets from IPv6
    if hostname.startswith("[") and hostname.endswith("]"):
        hostname = hostname[1:-1]
    return hostname in _LOCAL_HOSTS


# ── Main client ──────────────────────────────────────────────────────


class CloudApiClient:
    """HTTP client with strategy-chain connection support.

    The default mode ``auto`` tries secure → proxy → compat fallback.
    Explicit modes use a single strategy without fallback.
    """

    def __init__(
        self,
        base_url: str | None = None,
        access_token: str | None = None,
        mode: CloudNetworkMode | None = None,
        preferred_mode: str | None = None,
    ):
        original_url = (
            base_url or os.environ.get("ZHANGSHU_CLOUD_API_BASE_URL", "")
        ).rstrip("/")
        self._access_token = access_token or ""
        self._mode: CloudNetworkMode = mode or "auto"
        self._preferred_mode = preferred_mode  # Try this first in auto mode
        self._last_working_mode: str | None = None

        parsed = urlparse(original_url)
        self._original_base_url = original_url
        self._hostname = parsed.hostname or ""
        self._scheme = parsed.scheme or ""

        # Lazy-compute the IP-based URL for compat_no_sni mode
        self._ip_base_url: str | None = None
        self._parsed_url = parsed

    @property
    def is_configured(self) -> bool:
        return bool(self._original_base_url)

    def set_access_token(self, token: str) -> None:
        self._access_token = token

    @property
    def mode(self) -> CloudNetworkMode:
        return self._mode

    @mode.setter
    def mode(self, value: CloudNetworkMode) -> None:
        self._mode = value

    @property
    def last_working_mode(self) -> str | None:
        """The connection strategy that succeeded on the most recent request."""
        return self._last_working_mode

    def _get_ip_base_url(self) -> str:
        """Lazily compute the IP-based URL for compat_no_sni mode."""
        if self._ip_base_url is not None:
            return self._ip_base_url
        parsed = self._parsed_url
        if parsed.hostname and parsed.scheme == "https":
            ip = _resolve_ip(parsed.hostname)
            port = f":{parsed.port}" if parsed.port else ""
            self._ip_base_url = f"{parsed.scheme}://{ip}{port}"
        else:
            self._ip_base_url = self._original_base_url
        return self._ip_base_url

    # ── Internal: URL security check ─────────────────────────────────

    def _check_url_security(self) -> None:
        """Reject insecure remote HTTP. Allow HTTP only for local addresses."""
        if self._scheme == "http":
            parsed = urlparse(self._original_base_url)
            if not _is_local_url(parsed):
                raise CloudApiError(
                    "生产云服务必须使用 HTTPS，请将 ZHANGSHU_CLOUD_API_BASE_URL "
                    "改为 https://...",
                    error_kind="insecure_remote_http",
                    suggestion="请将云服务地址改为 HTTPS，或通过 Nginx/Caddy 配置 TLS。",
                )

    # ── Internal: headers ────────────────────────────────────────────

    def _base_headers(
        self, include_host: bool = False, *, method: str = "GET"
    ) -> dict[str, str]:
        headers: dict[str, str] = {}
        if method.upper() not in ("GET", "HEAD"):
            headers["Content-Type"] = "application/json"
        if include_host and self._hostname:
            headers["Host"] = self._hostname
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    # ── Internal: request with a specific mode ───────────────────────

    def _request_with_mode(
        self,
        mode: str,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> Any:
        """Execute a single request using the specified connection strategy.

        Returns parsed JSON, None for empty responses, or raises on error.
        """
        query = f"?{urlencode(params)}" if params else ""

        if mode == "compat_no_sni":
            url = f"{self._get_ip_base_url()}{path}{query}"
            headers = self._base_headers(include_host=True, method=method)
            client_kwargs: dict[str, Any] = dict(
                timeout=timeout,
                verify=_build_no_sni_context(),
                trust_env=False,
            )
        elif mode == "system_proxy":
            url = f"{self._original_base_url}{path}{query}"
            headers = self._base_headers(include_host=False, method=method)
            client_kwargs = dict(timeout=timeout, verify=True, trust_env=True)
        else:
            # secure_direct (and any unknown mode falls back to secure)
            url = f"{self._original_base_url}{path}{query}"
            headers = self._base_headers(include_host=False, method=method)
            client_kwargs = dict(timeout=timeout, verify=True, trust_env=False)

        try:
            with httpx.Client(**client_kwargs) as client:
                response = client.request(method, url, json=json, headers=headers)
        except httpx.HTTPError as exc:
            kind, suggestion = _classify_error(exc)
            raise CloudApiError(
                f"云服务请求失败：{exc}",
                error_kind=kind,
                suggestion=suggestion,
            ) from exc

        if response.status_code >= 400:
            message, err_kind, suggestion = _parse_remote_error(response)
            raise CloudApiError(
                message,
                status_code=response.status_code,
                error_kind=err_kind or "http_status_error",
                suggestion=suggestion,
            )

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    # ── Internal: main request dispatcher ────────────────────────────

    _NETWORK_ERROR_KINDS = frozenset({
        "tls_reset_or_sni_filtered",
        "tls_failed",
        "timeout",
        "tcp_unreachable",
        "dns_failed",
        "proxy_required_or_interfered",
        "cloud_unavailable",
    })

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> Any:
        self._ensure_configured()
        self._check_url_security()

        if self._mode != "auto":
            return self._request_with_mode(
                self._mode, method, path, json=json, params=params, timeout=timeout
            )

        # ── Auto strategy chain ──────────────────────────────────────
        # Use shorter timeout per strategy to avoid long waits
        auto_timeout = min(_AUTO_TIMEOUT, timeout)

        # Build strategy order: preferred mode first (if set), then the rest
        strategies = ["secure_direct", "system_proxy", "compat_no_sni"]
        if self._preferred_mode and self._preferred_mode in strategies:
            strategies.remove(self._preferred_mode)
            strategies.insert(0, self._preferred_mode)

        last_error: CloudApiError | None = None
        for mode in strategies:
            try:
                result = self._request_with_mode(
                    mode, method, path, json=json, params=params, timeout=auto_timeout
                )
                self._last_working_mode = mode
                return result
            except CloudApiError as exc:
                kind = exc.error_kind
                if kind not in self._NETWORK_ERROR_KINDS:
                    raise
                logger.info(
                    "Cloud API %s failed (%s), trying next strategy.",
                    mode, kind,
                )
                last_error = exc

        # All strategies failed
        raise CloudApiError(
            str(last_error),
            status_code=last_error.status_code if last_error else None,
            error_kind=last_error.error_kind if last_error else "cloud_unavailable",
            suggestion=(
                "所有连接模式均失败。请检查云服务地址、网络环境，"
                "或在应用设置中手动切换连接模式。"
            ),
        ) from last_error

    # ── Public API: configuration ────────────────────────────────────

    def _ensure_configured(self) -> None:
        if not self._original_base_url:
            raise CloudApiNotConfiguredError(
                "章枢云服务暂未配置，请联系管理员设置 ZHANGSHU_CLOUD_API_BASE_URL。"
            )

    # ── Public API: Auth ─────────────────────────────────────────────

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/login",
            json={"email": email, "password": password},
        )

    def login_with_email_code(
        self, email: str, verification_code: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/login/email-code",
            json={"email": email, "verification_code": verification_code},
        )

    def login_with_phone_code(
        self, phone_number: str, verification_code: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/login/phone-code",
            json={"phone_number": phone_number, "verification_code": verification_code},
        )

    def check_email(self, email: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/email/check",
            json={"email": email},
        )

    def check_phone(self, phone_number: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/phone/check",
            json={"phone_number": phone_number},
        )

    def send_email_code(self, email: str, purpose: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/email-code/send",
            json={"email": email, "purpose": purpose},
        )

    def send_phone_code(self, phone_number: str, purpose: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/phone-code/send",
            json={"phone_number": phone_number, "purpose": purpose},
        )

    def register(
        self,
        email: str,
        password: str,
        display_name: str,
        verification_code: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "display_name": display_name,
                "verification_code": verification_code,
            },
        )

    def register_with_phone(
        self, phone_number: str, verification_code: str, display_name: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/register/phone",
            json={
                "phone_number": phone_number,
                "verification_code": verification_code,
                "display_name": display_name,
            },
        )

    def start_oauth_login(self, provider: str) -> dict[str, Any]:
        return self._request("POST", f"/api/auth/oauth/{provider}/start", json={})

    def poll_oauth_login(self, session_id: str, poll_token: str) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/api/auth/oauth/session/{session_id}",
            params={"poll_token": poll_token},
        )

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    def get_me(self) -> dict[str, Any]:
        return self._request("GET", "/api/auth/me")

    # ── Public API: Backups ──────────────────────────────────────────

    def init_backup_upload(
        self, cloud_project_id: str, filename: str, size_bytes: int
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/projects/{cloud_project_id}/backups/init",
            json={"filename": filename, "size_bytes": size_bytes},
        )

    def upload_backup(
        self, upload_url: str, content: bytes, *, timeout: float = 120.0
    ) -> None:
        """Upload backup bytes to a presigned URL (OSS).

        This connects to OSS, not the cloud API, so it does NOT use the
        No-SNI strategy. It respects the connection mode for proxy settings.

        Uses trust_env=False by default. If mode is system_proxy, allows proxy.
        """
        self._ensure_configured()
        trust_env = self._mode == "system_proxy"
        try:
            with httpx.Client(timeout=timeout, trust_env=trust_env) as client:
                response = client.put(
                    upload_url,
                    content=content,
                    headers={"Content-Type": "application/zip"},
                )
        except httpx.HTTPError as exc:
            kind, suggestion = _classify_error(exc)
            raise CloudApiError(
                f"上传备份失败：{exc}",
                error_kind=kind,
                suggestion=suggestion,
            ) from exc
        if response.status_code >= 400:
            # Parse OSS XML error — extract Code/Message only, no full URL
            detail = _parse_oss_error(response.text)
            if response.status_code == 403:
                raise CloudApiError(
                    f"上传备份失败 (403)：{detail}",
                    status_code=403,
                    error_kind="oss_forbidden_or_signature_error",
                    suggestion=(
                        "可能原因：签名过期、Content-Type 不匹配、"
                        "CORS 配置不足或 OSS endpoint 内外网错误。"
                    ),
                )
            raise CloudApiError(
                f"上传备份失败 ({response.status_code})：{detail}",
                status_code=response.status_code,
                error_kind="oss_forbidden_or_signature_error",
            )

    def complete_backup(
        self, cloud_project_id: str, upload_id: str, checksum_sha256: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/projects/{cloud_project_id}/backups/complete",
            json={
                "upload_id": upload_id,
                "checksum_sha256": checksum_sha256,
            },
        )

    def list_backups(self, cloud_project_id: str) -> dict[str, Any]:
        return self._request(
            "GET", f"/api/projects/{cloud_project_id}/backups"
        )

    def get_backup_download_url(
        self, cloud_project_id: str, cloud_backup_id: str
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/api/projects/{cloud_project_id}/backups/{cloud_backup_id}/download-url",
        )

    def delete_backup(
        self, cloud_project_id: str, cloud_backup_id: str
    ) -> None:
        self._request(
            "DELETE",
            f"/api/projects/{cloud_project_id}/backups/{cloud_backup_id}",
        )

    # ── Public API: Projects ─────────────────────────────────────────

    def create_cloud_project(self, title: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/projects",
            json={"title": title},
        )

    def get_cloud_projects(self) -> dict[str, Any]:
        return self._request("GET", "/api/projects")

    # ── Public API: Account ──────────────────────────────────────────

    def get_account_profile(self) -> dict[str, Any]:
        return self._request("GET", "/api/account/profile")

    def update_account_profile(
        self,
        display_name: str | None = None,
        signature: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if display_name is not None:
            payload["display_name"] = display_name
        if signature is not None:
            payload["signature"] = signature
        return self._request("PATCH", "/api/account/profile", json=payload)

    def send_bind_email_code(self, email: str) -> dict[str, Any]:
        return self._request(
            "POST", "/api/account/bind/email-code/send", json={"email": email}
        )

    def send_bind_phone_code(self, phone_number: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/account/bind/phone-code/send",
            json={"phone_number": phone_number},
        )

    def bind_email(self, email: str, verification_code: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/account/bind/email",
            json={"email": email, "verification_code": verification_code},
        )

    def bind_phone(self, phone_number: str, verification_code: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/account/bind/phone",
            json={"phone_number": phone_number, "verification_code": verification_code},
        )

    def change_password(
        self, old_password: str, new_password: str
    ) -> dict[str, Any]:
        return self._request(
            "POST", "/api/account/password/change",
            json={"old_password": old_password, "new_password": new_password},
        )

    # ── Public API: Avatar ───────────────────────────────────────────

    def init_avatar_upload(
        self, filename: str, content_type: str, size_bytes: int
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/account/avatar/init",
            json={
                "filename": filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
            },
        )

    def upload_avatar(
        self, upload_url: str, content: bytes, content_type: str, *, timeout: float = 60.0
    ) -> None:
        """Upload avatar bytes to a presigned URL (OSS).

        Same pattern as upload_backup — connects to OSS, not cloud API.
        """
        self._ensure_configured()
        trust_env = self._mode == "system_proxy"
        try:
            with httpx.Client(timeout=timeout, trust_env=trust_env) as client:
                response = client.put(
                    upload_url,
                    content=content,
                    headers={"Content-Type": content_type},
                )
        except httpx.HTTPError as exc:
            kind, suggestion = _classify_error(exc)
            raise CloudApiError(
                f"上传头像失败：{exc}",
                error_kind=kind,
                suggestion=suggestion,
            ) from exc
        if response.status_code >= 400:
            detail = _parse_oss_error(response.text)
            raise CloudApiError(
                f"上传头像失败 ({response.status_code})：{detail}",
                status_code=response.status_code,
                error_kind="oss_forbidden_or_signature_error",
            )

    def complete_avatar_upload(
        self,
        upload_id: str,
        object_key: str,
        content_type: str,
        checksum_sha256: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/account/avatar/complete",
            json={
                "upload_id": upload_id,
                "object_key": object_key,
                "content_type": content_type,
                "checksum_sha256": checksum_sha256,
            },
        )

    def delete_avatar(self) -> dict[str, Any] | None:
        return self._request("DELETE", "/api/account/avatar")

    def list_sessions(self) -> dict[str, Any]:
        return self._request("GET", "/api/account/sessions")

    def revoke_all_sessions(self) -> dict[str, Any]:
        return self._request("POST", "/api/account/sessions/revoke-all")

    def get_usage(self) -> dict[str, Any]:
        return self._request("GET", "/api/account/usage")

    def export_account_data(self) -> dict[str, Any]:
        return self._request("GET", "/api/account/export")

    def request_account_deletion(self, password: str) -> dict[str, Any]:
        return self._request(
            "POST", "/api/account/delete-request",
            json={"password": password},
        )

    def confirm_account_deletion(
        self, request_id: str, confirmation_text: str
    ) -> dict[str, Any]:
        return self._request(
            "DELETE", "/api/account",
            json={"request_id": request_id, "confirmation_text": confirmation_text},
        )

    # ── Public API: Announcements ────────────────────────────────────

    def list_announcements(
        self,
        platform: str | None = None,
        app_version: str | None = None,
    ) -> dict[str, Any]:
        params: list[str] = []
        if platform:
            params.append(f"platform={platform}")
        if app_version:
            params.append(f"app_version={app_version}")
        query = f"?{'&'.join(params)}" if params else ""
        return self._request("GET", f"/api/announcements{query}")

    # ── Public API: Feedback ─────────────────────────────────────────

    def create_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/feedback", json=payload)

    def upload_feedback_attachment(
        self,
        upload_url: str,
        content: bytes,
        content_type: str,
        *,
        timeout: float = 120.0,
    ) -> None:
        """Upload a feedback attachment to a presigned URL (OSS).

        Same pattern as upload_backup — connects to OSS, not cloud API.
        """
        self._ensure_configured()
        trust_env = self._mode == "system_proxy"
        try:
            with httpx.Client(timeout=timeout, trust_env=trust_env) as client:
                response = client.put(
                    upload_url,
                    content=content,
                    headers={"Content-Type": content_type},
                )
        except httpx.HTTPError as exc:
            kind, suggestion = _classify_error(exc)
            raise CloudApiError(
                f"上传反馈附件失败：{exc}",
                error_kind=kind,
                suggestion=suggestion,
            ) from exc
        if response.status_code >= 400:
            detail = _parse_oss_error(response.text)
            raise CloudApiError(
                f"上传反馈附件失败 ({response.status_code})：{detail}",
                status_code=response.status_code,
                error_kind="oss_forbidden_or_signature_error",
            )

    def complete_feedback(
        self, feedback_id: str, uploads: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/feedback/{feedback_id}/complete",
            json={"uploads": uploads},
        )

    def list_feedback_replies(self, feedback_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/feedback/{feedback_id}/replies")

    def list_user_feedback(
        self, *, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        return self._request(
            "GET", f"/api/feedback?limit={limit}&offset={offset}"
        )

    # ── Public API: Incremental Sync ────────────────────────────────

    def sync_push(
        self,
        cloud_project_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Push local changes to the cloud sync endpoint."""
        return self._request(
            "POST",
            f"/api/projects/{cloud_project_id}/sync/push",
            json=payload,
        )

    def sync_pull(
        self,
        cloud_project_id: str,
        cursor: int = 0,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Pull remote changes since cursor."""
        return self._request(
            "GET",
            f"/api/projects/{cloud_project_id}/sync/pull?cursor={cursor}&limit={limit}",
        )

    def list_sync_snapshots(
        self,
        cloud_project_id: str,
        entity_type: str,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """List cloud sync snapshots for a specific entity."""
        return self._request(
            "GET",
            f"/api/projects/{cloud_project_id}/sync/snapshots"
            f"?entity_type={entity_type}&entity_id={entity_id}",
        )

    def list_sync_conflicts(
        self,
        cloud_project_id: str,
        resolved: bool = False,
    ) -> list[dict[str, Any]]:
        """List cloud sync conflicts for a project."""
        resolved_str = "true" if resolved else "false"
        return self._request(
            "GET",
            f"/api/projects/{cloud_project_id}/sync/conflicts?resolved={resolved_str}",
        )


# ── OSS error parsing ────────────────────────────────────────────────


def _parse_oss_error(body: str) -> str:
    """Extract Code and Message from OSS XML error response.

    Returns a short string; never includes full URLs or signatures.
    """
    if not body:
        return "未知错误"
    try:
        import re

        code_match = re.search(r"<Code>(.*?)</Code>", body)
        msg_match = re.search(r"<Message>(.*?)</Message>", body)
        code = code_match.group(1) if code_match else ""
        msg = msg_match.group(1) if msg_match else ""
        if code and msg:
            return f"{code}: {msg}"
        if code:
            return code
        return body[:200]
    except Exception:
        return body[:200]
