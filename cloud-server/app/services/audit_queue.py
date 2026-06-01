"""Audit event queue — Redis-backed with DB fallback.

When ``settings.audit_async_enabled`` is True and Redis is available,
audit events are pushed to a Redis list (RPUSH) instead of being
written synchronously to the database.  A separate worker
(:mod:`app.workers.audit_worker`) pops events in batches and inserts
them into ``audit_logs``.

If Redis is unavailable, the caller should fall back to synchronous DB
writes — this module does not make that decision.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AuditQueueError(Exception):
    """Raised when the audit queue cannot enqueue/dequeue."""


def _get_redis():
    """Return the Redis client or raise ``AuditQueueError``."""
    from app.core.redis_client import RedisUnavailable, get_redis_client

    try:
        return get_redis_client()
    except RedisUnavailable as exc:
        raise AuditQueueError(f"Redis unavailable: {exc}") from exc


def _queue_key() -> str:
    return get_settings().audit_queue_name


def enqueue_audit_event(payload: dict[str, Any]) -> None:
    """Push a single audit event payload to the Redis queue.

    The payload must already be filtered (no forbidden keys, no raw IPs).
    Raises :class:`AuditQueueError` if Redis is unavailable.
    """
    r = _get_redis()
    try:
        data = json.dumps(payload, ensure_ascii=False, default=str)
        r.rpush(_queue_key(), data)
    except Exception as exc:
        raise AuditQueueError(f"Redis RPUSH failed: {exc}") from exc


def dequeue_batch(batch_size: int) -> list[dict[str, Any]]:
    """Pop up to *batch_size* events from the Redis queue.

    Uses LPOP in a loop.  Returns an empty list when the queue is empty.
    Raises :class:`AuditQueueError` if Redis is unavailable.
    """
    r = _get_redis()
    events: list[dict[str, Any]] = []
    try:
        for _ in range(batch_size):
            raw = r.lpop(_queue_key())
            if raw is None:
                break
            events.append(json.loads(raw))
    except Exception as exc:
        raise AuditQueueError(f"Redis LPOP failed: {exc}") from exc
    return events


def queue_length() -> int:
    """Return the current queue length (0 if Redis is unavailable)."""
    try:
        r = _get_redis()
        return r.llen(_queue_key()) or 0
    except Exception:
        return 0


def write_batch_to_db(events: list[dict[str, Any]], db: Session) -> int:
    """Bulk-insert audit events into the ``audit_logs`` table.

    Returns the number of rows inserted.  Raises on DB errors (caller
    should handle retry/requeue).
    """
    from app.models.audit_log import AuditLog

    if not events:
        return 0

    rows = []
    for ev in events:
        rows.append(
            AuditLog(
                id=ev["id"],
                event=ev["event"],
                request_id=ev.get("request_id", ""),
                client_ip=ev.get("client_ip", ""),
                user_id=ev.get("user_id", ""),
                project_id=ev.get("project_id", ""),
                backup_id=ev.get("backup_id", ""),
                result=ev.get("result", "success"),
                reason_code=ev.get("reason_code", ""),
                extra_json=ev.get("extra_json"),
                created_at=ev["created_at"],
                actor_user_id=ev.get("actor_user_id"),
                target_user_id=ev.get("target_user_id"),
                client_ip_hash=ev.get("client_ip_hash"),
                client_ip_masked=ev.get("client_ip_masked"),
            )
        )

    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)
