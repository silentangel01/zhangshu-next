"""User activity event data access layer."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user_activity_event import UserActivityEvent


class UserActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, event: UserActivityEvent, *, commit: bool = True) -> UserActivityEvent:
        self.db.add(event)
        if commit:
            self.db.commit()
            self.db.refresh(event)
        return event

    def count_distinct_users_since(self, since: datetime) -> int:
        return self.db.scalar(
            select(func.count(func.distinct(UserActivityEvent.user_id))).where(
                UserActivityEvent.user_id.isnot(None),
                UserActivityEvent.created_at >= since,
            )
        ) or 0

    def count_events_by_type_since(self, event_type: str, since: datetime) -> int:
        return self.db.scalar(
            select(func.count()).where(
                UserActivityEvent.event_type == event_type,
                UserActivityEvent.created_at >= since,
            )
        ) or 0

    def count_by_day(
        self, event_type: str, since: datetime, days: int
    ) -> list[dict]:
        """Return per-day counts for the last N days.

        Uses date truncation compatible with both SQLite and PostgreSQL.
        """
        date_col = func.date(UserActivityEvent.created_at)
        rows = (
            self.db.execute(
                select(date_col.label("day"), func.count().label("count"))
                .where(
                    UserActivityEvent.event_type == event_type,
                    UserActivityEvent.created_at >= since,
                )
                .group_by(date_col)
                .order_by(date_col)
            )
            .all()
        )
        return [{"day": str(r.day), "count": r.count} for r in rows]

    def list_recent_by_user(
        self, user_id: str, limit: int = 20
    ) -> list[UserActivityEvent]:
        return list(
            self.db.scalars(
                select(UserActivityEvent)
                .where(UserActivityEvent.user_id == user_id)
                .order_by(UserActivityEvent.created_at.desc())
                .limit(limit)
            )
        )
