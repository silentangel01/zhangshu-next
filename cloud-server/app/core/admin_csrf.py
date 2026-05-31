"""Lightweight CSRF / Origin protection for admin write endpoints.

For non-safe HTTP methods (POST/PATCH/PUT/DELETE) on ``/api/admin/*`` paths:

1. ``Origin`` or ``Referer`` must match one of the allowed admin origins
   (or same-origin when the lists are empty in development).
2. The request must carry the custom header ``X-Zhangshu-Admin-Request: 1``.

GET / HEAD / OPTIONS requests are always allowed.
Non-admin paths are always allowed.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from fastapi import HTTPException, Request

from app.core.config import Settings

logger = logging.getLogger(__name__)

_ADMIN_HEADER_NAME = "x-zhangshu-admin-request"
_ADMIN_HEADER_VALUE = "1"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _origin_from_request(request: Request) -> str | None:
    """Extract the origin from the Origin header, falling back to Referer."""
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return None


def validate_admin_write_request(request: Request, settings: Settings) -> None:
    """Validate an admin write request for CSRF / Origin protection.

    Raises ``HTTPException(403)`` on failure.
    """
    # Only check admin paths
    path = request.url.path
    if not path.startswith("/api/admin"):
        return

    # Safe methods are always allowed
    if request.method in _SAFE_METHODS:
        return

    # In development, if origin check is not required, skip all CSRF validation.
    # Production MUST enable this (enforced by validate_production_config).
    if not settings.admin_require_origin_check:
        return

    # Custom header check — required when origin checking is active.
    custom_header = request.headers.get(_ADMIN_HEADER_NAME, "")
    if custom_header != _ADMIN_HEADER_VALUE:
        raise HTTPException(
            status_code=403,
            detail="请求缺少安全验证 header (X-Zhangshu-Admin-Request)。",
        )

    # Origin / Referer check
    allowed_origins = settings.admin_allowed_origin_list
    if allowed_origins:
        request_origin = _origin_from_request(request)
        if request_origin is None:
            raise HTTPException(
                status_code=403,
                detail="缺少 Origin 或 Referer header，无法验证请求来源。",
            )
        # Normalize allowed origins for comparison
        allowed_set = {o.rstrip("/") for o in allowed_origins}
        if request_origin not in allowed_set:
            logger.warning(
                "Admin request from disallowed origin: %s (allowed: %s)",
                request_origin,
                allowed_set,
            )
            raise HTTPException(
                status_code=403,
                detail="请求来源不在管理员允许的域名列表中。",
            )
