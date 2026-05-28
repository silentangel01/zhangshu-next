"""Lightweight structured audit logging.

Audit events are written to the standard logger at INFO level with
structured fields, and optionally persisted to the ``audit_logs`` database
table when a SQLAlchemy ``Session`` is provided.

Sensitive data (passwords, tokens, OSS URLs) must NEVER be included.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_audit_logger = logging.getLogger("app.audit")

# Keys allowed in the ``extra`` dict — whitelisted to prevent accidental
# leakage of sensitive data into the persisted JSON column.
_ALLOWED_EXTRA_KEYS = frozenset({
    "file_name", "size_bytes", "status_code", "email_domain",
    "tokens_revoked", "target_user_id", "feedback_id", "announcement_id",
})


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
    db: Session | None = None,
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
    db:
        Optional SQLAlchemy session. When provided, the event is also
        persisted to the ``audit_logs`` database table.
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
    safe_extra: dict[str, Any] = {}
    if extra:
        for key, val in extra.items():
            if key in _ALLOWED_EXTRA_KEYS:
                fields[f"audit_{key}"] = val
                safe_extra[key] = val

    _audit_logger.info(
        "AUDIT %s | user=%s | result=%s",
        event,
        user_id or "anonymous",
        result,
        extra=fields,
    )

    # ── Persist to database ──────────────────────────────────────────────
    if db is not None:
        try:
            from app.models.audit_log import AuditLog, utc_now

            row = AuditLog(
                id=str(uuid.uuid4()),
                event=event,
                request_id=request_id or "",
                client_ip=client_ip or "",
                user_id=user_id or "",
                project_id=project_id or "",
                backup_id=backup_id or "",
                result=result or "success",
                reason_code=reason_code or "",
                extra_json=json.dumps(safe_extra, ensure_ascii=False) if safe_extra else None,
                created_at=utc_now(),
            )
            db.add(row)
            db.commit()
        except Exception:
            _audit_logger.warning("Failed to persist audit event to DB", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
