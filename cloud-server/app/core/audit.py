"""Lightweight structured audit logging.

Audit events are always written to the standard logger at INFO level
with structured fields.

Persistence strategy:

- **Async mode** (``settings.audit_async_enabled=True`` + Redis
  available): events are enqueued to a Redis list and flushed to the
  database by a separate worker process.  This removes the DB write
  from the request path.

- **Sync mode** (default, or Redis unavailable): events are persisted
  directly to the ``audit_logs`` table when a SQLAlchemy ``Session`` is
  provided.

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
    # Phase 4+: high-risk action metadata
    "action_reason", "risk_level", "new_status", "new_role", "old_role",
    "permission", "attachment_id", "target_role",
})

# Substrings that must NEVER appear in extra keys — blocked as a safety net.
_FORBIDDEN_KEY_SUBSTRINGS = frozenset({
    "password", "token", "secret", "access_key", "upload_url",
    "download_url", "authorization", "cookie",
})


def _is_forbidden_key(key: str) -> bool:
    """Check if an extra key name contains a forbidden substring."""
    lower = key.lower()
    return any(s in lower for s in _FORBIDDEN_KEY_SUBSTRINGS)


def _build_payload(
    event: str,
    *,
    request_id: str,
    masked_ip: str,
    user_id: str,
    project_id: str,
    backup_id: str,
    result: str,
    reason_code: str,
    safe_extra: dict[str, Any],
    client_ip: str,
) -> dict[str, Any]:
    """Build a DB-ready audit payload dict (no forbidden keys)."""
    from app.core.privacy import hash_ip
    from app.models.audit_log import utc_now

    target_uid = ""
    if safe_extra and "target_user_id" in safe_extra:
        target_uid = str(safe_extra["target_user_id"])

    return {
        "id": str(uuid.uuid4()),
        "event": event,
        "request_id": request_id or "",
        "client_ip": masked_ip,
        "user_id": user_id or "",
        "project_id": project_id or "",
        "backup_id": backup_id or "",
        "result": result or "success",
        "reason_code": reason_code or "",
        "extra_json": json.dumps(safe_extra, ensure_ascii=False) if safe_extra else None,
        "created_at": utc_now(),
        "actor_user_id": user_id or None,
        "target_user_id": target_uid or None,
        "client_ip_hash": hash_ip(client_ip) if client_ip else None,
        "client_ip_masked": masked_ip if client_ip else None,
    }


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
        Originating client IP address (will be masked before storage).
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
        persisted to the ``audit_logs`` database table (sync mode) or
        enqueued to Redis (async mode).
    """
    from app.core.privacy import mask_ip

    # Mask IP for logging — never store raw IP in structured fields
    masked_ip = mask_ip(client_ip)

    fields: dict[str, Any] = {
        "event": event,
        "request_id": request_id,
        "client_ip": masked_ip,
        "user_id": user_id,
        "project_id": project_id,
        "backup_id": backup_id,
        "result": result,
        "reason_code": reason_code,
    }
    safe_extra: dict[str, Any] = {}
    if extra:
        for key, val in extra.items():
            if _is_forbidden_key(key):
                _audit_logger.warning(
                    "Blocked forbidden key in audit extra: %s", key,
                )
                continue
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

    # ── Persist ──────────────────────────────────────────────────────────
    if db is None:
        return

    # Try async queue first
    try:
        from app.core.config import get_settings

        settings = get_settings()
        if settings.audit_async_enabled:
            payload = _build_payload(
                event,
                request_id=request_id,
                masked_ip=masked_ip,
                user_id=user_id,
                project_id=project_id,
                backup_id=backup_id,
                result=result,
                reason_code=reason_code,
                safe_extra=safe_extra,
                client_ip=client_ip,
            )
            from app.services.audit_queue import enqueue_audit_event

            enqueue_audit_event(payload)
            return  # Enqueued — worker will persist
    except Exception:
        _audit_logger.warning(
            "Audit async enqueue failed, falling back to sync DB write",
            exc_info=True,
        )

    # Sync fallback — direct DB write
    _persist_sync(
        event,
        request_id=request_id,
        masked_ip=masked_ip,
        user_id=user_id,
        project_id=project_id,
        backup_id=backup_id,
        result=result,
        reason_code=reason_code,
        safe_extra=safe_extra,
        client_ip=client_ip,
        db=db,
    )


def _persist_sync(
    event: str,
    *,
    request_id: str,
    masked_ip: str,
    user_id: str,
    project_id: str,
    backup_id: str,
    result: str,
    reason_code: str,
    safe_extra: dict[str, Any],
    client_ip: str,
    db: Session,
) -> None:
    """Persist an audit event directly to the database."""
    try:
        payload = _build_payload(
            event,
            request_id=request_id,
            masked_ip=masked_ip,
            user_id=user_id,
            project_id=project_id,
            backup_id=backup_id,
            result=result,
            reason_code=reason_code,
            safe_extra=safe_extra,
            client_ip=client_ip,
        )
        from app.models.audit_log import AuditLog

        row = AuditLog(**payload)
        db.add(row)
        db.commit()
    except Exception:
        _audit_logger.warning("Failed to persist audit event to DB", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
