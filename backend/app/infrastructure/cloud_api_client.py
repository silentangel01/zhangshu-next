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
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0

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
    ):
        original_url = (
            base_url or os.environ.get("ZHANGSHU_CLOUD_API_BASE_URL", "")
        ).rstrip("/")
        self._access_token = access_token or ""
        self._mode: CloudNetworkMode = mode or "auto"

        parsed = urlparse(original_url)
        self._original_base_url = original_url
        self._hostname = parsed.hostname or ""
        self._scheme = parsed.scheme or ""

        # Pre-compute the IP-based URL for compat_no_sni mode
        self._ip_base_url = original_url
        if parsed.hostname and parsed.scheme == "https":
            ip = _resolve_ip(parsed.hostname)
            port = f":{parsed.port}" if parsed.port else ""
            self._ip_base_url = f"{parsed.scheme}://{ip}{port}"

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

    def _base_headers(self, include_host: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
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
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> Any:
        """Execute a single request using the specified connection strategy.

        Returns parsed JSON, None for empty responses, or raises on error.
        """
        if mode == "compat_no_sni":
            url = f"{self._ip_base_url}{path}"
            headers = self._base_headers(include_host=True)
            client_kwargs: dict[str, Any] = dict(
                timeout=timeout,
                verify=_build_no_sni_context(),
                trust_env=False,
            )
        elif mode == "system_proxy":
            url = f"{self._original_base_url}{path}"
            headers = self._base_headers(include_host=False)
            client_kwargs = dict(timeout=timeout, verify=True, trust_env=True)
        else:
            # secure_direct (and any unknown mode falls back to secure)
            url = f"{self._original_base_url}{path}"
            headers = self._base_headers(include_host=False)
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
            detail = ""
            try:
                payload = response.json()
                if isinstance(payload, dict) and "detail" in payload:
                    detail = str(payload["detail"])
            except Exception:
                pass
            message = detail or f"云服务返回错误 ({response.status_code})"
            raise CloudApiError(
                message,
                status_code=response.status_code,
                error_kind="http_status_error",
            )

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    # ── Internal: main request dispatcher ────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> Any:
        self._ensure_configured()
        self._check_url_security()

        if self._mode != "auto":
            return self._request_with_mode(
                self._mode, method, path, json=json, timeout=timeout
            )

        # ── Auto strategy chain ──────────────────────────────────────
        # 1) Try secure_direct (full TLS, no proxy)
        try:
            return self._request_with_mode(
                "secure_direct", method, path, json=json, timeout=timeout
            )
        except CloudApiError as primary_error:
            kind = primary_error.error_kind
            # Non-network errors (401, 404, etc.) should not trigger fallback
            if kind not in (
                "tls_reset_or_sni_filtered",
                "tls_failed",
                "timeout",
                "tcp_unreachable",
                "dns_failed",
                "proxy_required_or_interfered",
                "cloud_unavailable",
            ):
                raise

            logger.info(
                "Cloud API secure_direct failed (%s), trying system_proxy.",
                kind,
            )

        # 2) Try system_proxy (allows HTTP_PROXY/HTTPS_PROXY)
        try:
            return self._request_with_mode(
                "system_proxy", method, path, json=json, timeout=timeout
            )
        except CloudApiError as proxy_error:
            kind = proxy_error.error_kind
            if kind not in (
                "tls_reset_or_sni_filtered",
                "tls_failed",
                "timeout",
                "tcp_unreachable",
                "dns_failed",
                "proxy_required_or_interfered",
                "cloud_unavailable",
            ):
                raise

            logger.info(
                "Cloud API system_proxy failed (%s), trying compat_no_sni.",
                kind,
            )

        # 3) Try compat_no_sni (IP direct + Host header, no cert verification)
        try:
            return self._request_with_mode(
                "compat_no_sni", method, path, json=json, timeout=timeout
            )
        except CloudApiError as compat_error:
            # All strategies failed — raise the most informative error
            raise CloudApiError(
                str(compat_error),
                status_code=compat_error.status_code,
                error_kind=compat_error.error_kind,
                suggestion=(
                    "所有连接模式均失败。请检查云服务地址、网络环境，"
                    "或在应用设置中手动切换连接模式。"
                ),
            ) from compat_error

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

    def register(
        self, email: str, password: str, display_name: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "display_name": display_name,
            },
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
