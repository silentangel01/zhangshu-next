"""Low-level cloud network diagnostic tools.

Each diagnostic step runs independently and returns a structured result.
Diagnostics NEVER include passwords, tokens, refresh tokens, or full OSS URLs.
"""

from __future__ import annotations

import logging
import os
import socket
import ssl
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.infrastructure.cloud_api_client import _build_no_sni_context, _resolve_ip

logger = logging.getLogger(__name__)

# Local addresses exempt from HTTPS requirement
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# Diagnostic timeout (seconds) per step
_STEP_TIMEOUT = 10.0


def _make_step(
    name: str,
    ok: bool,
    latency_ms: float | None = None,
    error_kind: str = "",
    message: str = "",
    suggestion: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "latency_ms": round(latency_ms) if latency_ms is not None else None,
        "error_kind": error_kind,
        "message": message,
        "suggestion": suggestion,
    }


def _get_base_url() -> str:
    return os.environ.get("ZHANGSHU_CLOUD_API_BASE_URL", "").rstrip("/")


def _is_local_host(hostname: str) -> bool:
    h = hostname.lower()
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1]
    return h in _LOCAL_HOSTS


# ── Step 1: config_check ─────────────────────────────────────────────


def config_check() -> dict[str, Any]:
    """Check whether ZHANGSHU_CLOUD_API_BASE_URL is configured."""
    url = _get_base_url()
    if not url:
        return _make_step(
            "config_check",
            ok=False,
            error_kind="not_configured",
            message="未配置云服务地址。",
            suggestion="请设置环境变量 ZHANGSHU_CLOUD_API_BASE_URL。",
        )

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return _make_step(
            "config_check",
            ok=False,
            error_kind="invalid_url",
            message=f"云服务地址 scheme 无效: {parsed.scheme}",
            suggestion="地址应以 https:// 开头。",
        )

    return _make_step(
        "config_check",
        ok=True,
        message=f"已配置：{parsed.scheme}://{parsed.hostname}",
    )


# ── Step 2: https_policy_check ───────────────────────────────────────


def https_policy_check() -> dict[str, Any]:
    """Verify remote URLs use HTTPS; local addresses may use HTTP."""
    url = _get_base_url()
    if not url:
        return _make_step(
            "https_policy_check",
            ok=False,
            error_kind="not_configured",
            message="未配置云服务地址，跳过 HTTPS 检查。",
        )

    parsed = urlparse(url)
    if parsed.scheme == "https":
        return _make_step(
            "https_policy_check",
            ok=True,
            message="云服务地址使用 HTTPS。",
        )

    if _is_local_host(parsed.hostname or ""):
        return _make_step(
            "https_policy_check",
            ok=True,
            message=f"本地开发地址 ({parsed.hostname}) 允许 HTTP。",
        )

    return _make_step(
        "https_policy_check",
        ok=False,
        error_kind="insecure_remote_http",
        message="远程云服务地址使用 HTTP，数据将被明文传输。",
        suggestion="请将地址改为 HTTPS，或通过 Nginx/Caddy 配置 TLS。",
    )


# ── Step 3: dns_check ────────────────────────────────────────────────


def dns_check() -> dict[str, Any]:
    """Resolve hostname and return IP list."""
    url = _get_base_url()
    if not url:
        return _make_step("dns_check", ok=False, error_kind="not_configured")

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if not hostname:
        return _make_step("dns_check", ok=False, error_kind="invalid_url")

    start = time.monotonic()
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_INET)
        ips = list({r[4][0] for r in results})
        elapsed = (time.monotonic() - start) * 1000
        return _make_step(
            "dns_check",
            ok=True,
            latency_ms=elapsed,
            message=f"解析成功：{', '.join(ips)}",
        )
    except socket.gaierror:
        elapsed = (time.monotonic() - start) * 1000
        return _make_step(
            "dns_check",
            ok=False,
            latency_ms=elapsed,
            error_kind="dns_failed",
            message=f"DNS 解析失败: {hostname}",
            suggestion="请检查云服务地址是否正确，或检查 DNS 设置。",
        )


# ── Step 4: tcp_check ────────────────────────────────────────────────


def tcp_check() -> dict[str, Any]:
    """Test TCP connectivity to host:port."""
    url = _get_base_url()
    if not url:
        return _make_step("tcp_check", ok=False, error_kind="not_configured")

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    start = time.monotonic()
    try:
        with socket.create_connection((hostname, port), timeout=_STEP_TIMEOUT):
            elapsed = (time.monotonic() - start) * 1000
            return _make_step(
                "tcp_check",
                ok=True,
                latency_ms=elapsed,
                message=f"TCP 连接 {hostname}:{port} 成功。",
            )
    except (socket.timeout, TimeoutError):
        elapsed = (time.monotonic() - start) * 1000
        return _make_step(
            "tcp_check",
            ok=False,
            latency_ms=elapsed,
            error_kind="tcp_unreachable",
            message=f"TCP 连接 {hostname}:{port} 超时。",
            suggestion="云服务可能不可达，或防火墙阻止了该端口。",
        )
    except OSError as exc:
        elapsed = (time.monotonic() - start) * 1000
        return _make_step(
            "tcp_check",
            ok=False,
            latency_ms=elapsed,
            error_kind="tcp_unreachable",
            message=f"TCP 连接失败: {exc}",
            suggestion="请检查云服务地址和网络连接。",
        )


# ── Step 5: secure_https_check ───────────────────────────────────────


def secure_https_check() -> dict[str, Any]:
    """Full TLS with SNI + certificate verification GET /health."""
    url = _get_base_url()
    if not url:
        return _make_step("secure_https_check", ok=False, error_kind="not_configured")

    parsed = urlparse(url)
    if parsed.scheme != "https":
        return _make_step(
            "secure_https_check",
            ok=False,
            error_kind="insecure_remote_http",
            message="非 HTTPS 地址，跳过 TLS 检查。",
        )

    health_url = f"{url}/health"
    start = time.monotonic()
    try:
        with httpx.Client(
            timeout=_STEP_TIMEOUT,
            verify=True,
            trust_env=False,
        ) as client:
            resp = client.get(health_url)
            elapsed = (time.monotonic() - start) * 1000
            if resp.status_code == 200:
                return _make_step(
                    "secure_https_check",
                    ok=True,
                    latency_ms=elapsed,
                    message="安全 HTTPS 连接成功。",
                )
            return _make_step(
                "secure_https_check",
                ok=False,
                latency_ms=elapsed,
                error_kind="http_status_error",
                message=f"HTTPS 请求返回 {resp.status_code}。",
                suggestion="服务端可能存在问题，请检查云服务状态。",
            )
    except httpx.ConnectError as exc:
        elapsed = (time.monotonic() - start) * 1000
        exc_str = str(exc).lower()
        if "10054" in str(exc) or "reset" in exc_str or "forcibly" in exc_str:
            return _make_step(
                "secure_https_check",
                ok=False,
                latency_ms=elapsed,
                error_kind="tls_reset_or_sni_filtered",
                message="HTTPS 连接被重置，可能被校园/公司网络拦截。",
                suggestion="可尝试系统代理或兼容模式。",
            )
        return _make_step(
            "secure_https_check",
            ok=False,
            latency_ms=elapsed,
            error_kind="tls_failed",
            message=f"HTTPS 连接失败: {exc}",
            suggestion="请检查网络连接和证书配置。",
        )
    except httpx.HTTPError as exc:
        elapsed = (time.monotonic() - start) * 1000
        return _make_step(
            "secure_https_check",
            ok=False,
            latency_ms=elapsed,
            error_kind="tls_failed",
            message=f"HTTPS 请求失败: {exc}",
            suggestion="请检查网络连接。",
        )


# ── Step 6: system_proxy_check ───────────────────────────────────────


def system_proxy_check() -> dict[str, Any]:
    """TLS with system proxy (trust_env=True) GET /health."""
    url = _get_base_url()
    if not url:
        return _make_step("system_proxy_check", ok=False, error_kind="not_configured")

    parsed = urlparse(url)
    if parsed.scheme != "https":
        return _make_step(
            "system_proxy_check",
            ok=False,
            error_kind="insecure_remote_http",
            message="非 HTTPS 地址，跳过代理检查。",
        )

    health_url = f"{url}/health"
    start = time.monotonic()
    try:
        with httpx.Client(
            timeout=_STEP_TIMEOUT,
            verify=True,
            trust_env=True,
        ) as client:
            resp = client.get(health_url)
            elapsed = (time.monotonic() - start) * 1000
            if resp.status_code == 200:
                return _make_step(
                    "system_proxy_check",
                    ok=True,
                    latency_ms=elapsed,
                    message="通过系统代理连接成功。",
                )
            return _make_step(
                "system_proxy_check",
                ok=False,
                latency_ms=elapsed,
                error_kind="http_status_error",
                message=f"代理请求返回 {resp.status_code}。",
            )
    except httpx.ConnectError as exc:
        elapsed = (time.monotonic() - start) * 1000
        exc_str = str(exc).lower()
        if "proxy" in exc_str:
            return _make_step(
                "system_proxy_check",
                ok=False,
                latency_ms=elapsed,
                error_kind="proxy_required_or_interfered",
                message=f"代理连接异常: {exc}",
                suggestion="请检查代理软件设置，或尝试关闭代理后使用直连模式。",
            )
        if "10054" in str(exc) or "reset" in exc_str:
            return _make_step(
                "system_proxy_check",
                ok=False,
                latency_ms=elapsed,
                error_kind="tls_reset_or_sni_filtered",
                message="通过代理连接仍被重置。",
                suggestion="代理可能未能正确转发请求，请尝试其他代理或兼容模式。",
            )
        return _make_step(
            "system_proxy_check",
            ok=False,
            latency_ms=elapsed,
            error_kind="tls_failed",
            message=f"代理连接失败: {exc}",
        )
    except httpx.HTTPError as exc:
        elapsed = (time.monotonic() - start) * 1000
        return _make_step(
            "system_proxy_check",
            ok=False,
            latency_ms=elapsed,
            error_kind="cloud_unavailable",
            message=f"代理请求失败: {exc}",
        )


# ── Step 7: compat_no_sni_check ──────────────────────────────────────


def compat_no_sni_check() -> dict[str, Any]:
    """IP direct + Host header + No-SNI TLS GET /health."""
    url = _get_base_url()
    if not url:
        return _make_step("compat_no_sni_check", ok=False, error_kind="not_configured")

    parsed = urlparse(url)
    if parsed.scheme != "https":
        return _make_step(
            "compat_no_sni_check",
            ok=False,
            error_kind="insecure_remote_http",
            message="非 HTTPS 地址，跳过兼容模式检查。",
        )

    hostname = parsed.hostname or ""
    ip = _resolve_ip(hostname)
    port = f":{parsed.port}" if parsed.port else ""
    ip_url = f"https://{ip}{port}/health"

    headers: dict[str, str] = {}
    if hostname:
        headers["Host"] = hostname

    start = time.monotonic()
    try:
        with httpx.Client(
            timeout=_STEP_TIMEOUT,
            verify=_build_no_sni_context(),
            trust_env=False,
        ) as client:
            resp = client.get(ip_url, headers=headers)
            elapsed = (time.monotonic() - start) * 1000
            if resp.status_code == 200:
                return _make_step(
                    "compat_no_sni_check",
                    ok=True,
                    latency_ms=elapsed,
                    message="兼容模式 (IP 直连) 连接成功。",
                    suggestion="当前网络可能需要使用兼容模式。",
                )
            return _make_step(
                "compat_no_sni_check",
                ok=False,
                latency_ms=elapsed,
                error_kind="http_status_error",
                message=f"兼容模式请求返回 {resp.status_code}。",
            )
    except httpx.ConnectError as exc:
        elapsed = (time.monotonic() - start) * 1000
        return _make_step(
            "compat_no_sni_check",
            ok=False,
            latency_ms=elapsed,
            error_kind="tcp_unreachable",
            message=f"兼容模式连接失败: {exc}",
            suggestion="当前网络可能同时封锁 IP 直连，请更换网络或使用可信代理。",
        )
    except httpx.HTTPError as exc:
        elapsed = (time.monotonic() - start) * 1000
        return _make_step(
            "compat_no_sni_check",
            ok=False,
            latency_ms=elapsed,
            error_kind="cloud_unavailable",
            message=f"兼容模式请求失败: {exc}",
        )


# ── Run all steps ────────────────────────────────────────────────────


def run_all_diagnostics() -> list[dict[str, Any]]:
    """Run all diagnostic steps and return results."""
    steps: list[dict[str, Any]] = []
    for fn in (
        config_check,
        https_policy_check,
        dns_check,
        tcp_check,
        secure_https_check,
        system_proxy_check,
        compat_no_sni_check,
    ):
        try:
            steps.append(fn())
        except Exception as exc:
            name = fn.__name__.replace("_", " ")
            steps.append(
                _make_step(
                    fn.__name__.replace("_check", ""),
                    ok=False,
                    error_kind="unknown",
                    message=f"诊断步骤 {name} 异常: {exc}",
                )
            )
    return steps
