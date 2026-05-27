"""Activity event recording service.

Records low-sensitivity user behavior events for admin dashboard metrics.
NEVER stores: tokens, passwords, presigned URLs, feedback content, or
plaintext IP addresses.
"""

from __future__ import annotations

import hashlib
import json
import logging
from uuid import uuid4

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.user_activity_event import UserActivityEvent, utc_now
from app.repositories.user_activity_repo import UserActivityRepository

logger = logging.getLogger(__name__)

# Whitelist of allowed metadata keys — reject everything else
_ALLOWED_METADATA_KEYS = frozenset({
    "status_code",
    "category",
    "size_bytes",
    "cloud_project_id",
    "feedback_id",
    "backup_id",
    "result",
})


def _hash_ip(ip: str | None) -> str | None:
    """SHA-256 hash of client IP — never store plaintext."""
    if not ip or ip == "unknown":
        return None
    return hashlib.sha256(ip.encode()).hexdigest()


def _sanitize_metadata(metadata: dict | None) -> str | None:
    """Filter metadata to only whitelisted keys, return as JSON string."""
    if not metadata:
        return None
    filtered = {k: v for k, v in metadata.items() if k in _ALLOWED_METADATA_KEYS}
    if not filtered:
        return None
    return json.dumps(filtered, ensure_ascii=False)


def _truncate_ua(ua: str | None) -> str | None:
    """Truncate user-agent to 255 chars."""
    if not ua:
        return None
    return ua[:255]


class ActivityService:
    """Records user activity events to the database."""

    def __init__(self, db: Session):
        self._db = db
        self._repo = UserActivityRepository(db)

    def record(
        self,
        user_id: str | None,
        event_type: str,
        request: Request | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Record a single activity event.

        Args:
            user_id: The user who triggered the event (None for anonymous).
            event_type: e.g. "login_success", "user_registered", "backup_complete".
            request: FastAPI Request to extract IP and user-agent from.
            metadata: Optional dict with only whitelisted keys.
        """
        client_ip = None
        user_agent = None

        if request is not None:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            elif request.client:
                client_ip = request.client.host
            user_agent = request.headers.get("user-agent", "")

        event = UserActivityEvent(
            id=str(uuid4()),
            user_id=user_id,
            event_type=event_type,
            client_ip_hash=_hash_ip(client_ip),
            user_agent=_truncate_ua(user_agent),
            metadata_json=_sanitize_metadata(metadata),
            created_at=utc_now(),
        )

        try:
            self._repo.create(event)
        except Exception:
            # Activity recording must never break the main request flow
            logger.warning("Failed to record activity event: %s", event_type, exc_info=True)
            try:
                self._db.rollback()
            except Exception:
                pass
