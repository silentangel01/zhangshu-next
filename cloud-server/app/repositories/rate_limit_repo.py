"""Rate limit event data access layer."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.rate_limit_event import RateLimitEvent, utc_now


class RateLimitRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_active(self, scope: str, key: str, window_start: datetime) -> int:
        """Count non-expired events for the given scope+key since *window_start*."""
        return self.db.scalar(
            select(func.count()).select_from(RateLimitEvent).where(
                RateLimitEvent.scope == scope,
                RateLimitEvent.key == key,
                RateLimitEvent.created_at >= window_start,
                RateLimitEvent.expires_at > utc_now(),
            )
        ) or 0

    def create(
        self, event: RateLimitEvent, *, commit: bool = True
    ) -> RateLimitEvent:
        self.db.add(event)
        if commit:
            self.db.commit()
            self.db.refresh(event)
        return event

    def purge_expired(self, *, commit: bool = True) -> int:
        """Delete all expired events. Returns the number of rows removed."""
        now = utc_now()
        result = self.db.execute(
            delete(RateLimitEvent).where(RateLimitEvent.expires_at <= now)
        )
        if commit:
            self.db.commit()
        return result.rowcount
