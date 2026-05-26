"""Lightweight structured audit logging.

Audit events are written to the standard logger at INFO level with
structured fields — no database table required for V1.

Sensitive data (passwords, tokens, OSS URLs) must NEVER be included.
"""

from __future__ import annotations

import logging
from typing import Any

_audit_logger = logging.getLogger("app.audit")


def audit_event(
    event: str,
    *,
    request_id: str = "",
    client_ip: str = "",
    user_id: str = "",
    project_id: str = "",
    backup_id: str = "",
    result: str = "success",
    reason_code: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    """Log a structured audit event.

    Parameters
    ----------
    event:
        Event type identifier (e.g. ``login_success``, ``backup_init``).
    request_id:
        Current request correlation ID.
    client_ip:
        Originating client IP address.
    user_id:
        Authenticated user ID (empty for anonymous events like login_failed).
    project_id:
        Related project ID, if applicable.
    backup_id:
        Related backup ID, if applicable.
    result:
        Outcome — ``success``, ``failure``, ``error``.
    reason_code:
        Machine-readable reason for failures (e.g. ``rate_limited``, ``quota_exceeded``).
    extra:
        Additional non-sensitive key-value pairs.
    """
    fields: dict[str, Any] = {
        "event": event,
        "request_id": request_id,
        "client_ip": client_ip,
        "user_id": user_id,
        "project_id": project_id,
        "backup_id": backup_id,
        "result": result,
        "reason_code": reason_code,
    }
    if extra:
        # Whitelist extra keys — never pass through raw sensitive data.
        # Prefix with "audit_" to avoid clashing with LogRecord reserved names.
        for key, val in extra.items():
            if key in ("file_name", "size_bytes", "status_code", "email_domain"):
                fields[f"audit_{key}"] = val

    _audit_logger.info(
        "AUDIT %s | user=%s | result=%s",
        event,
        user_id or "anonymous",
        result,
        extra=fields,
    )
