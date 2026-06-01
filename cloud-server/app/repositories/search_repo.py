"""Admin search data access layer.

Isolates the SQL queries for admin global search from the service and
API layers. PostgreSQL uses trigram-friendly ``ILIKE`` queries that
benefit from the ``pg_trgm`` GIN indexes. SQLite uses the same
``ILIKE`` syntax but is only used for development with strict limits.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.announcement import Announcement
from app.models.feedback_ticket import FeedbackTicket
from app.models.user import User


class SearchRepository:
    def __init__(self, db: Session):
        self._db = db

    def search_users(
        self, q: str, limit: int, *, include_deleted: bool = False
    ) -> list[dict[str, Any]]:
        pattern = f"%{q}%"
        stmt = (
            select(User.id, User.email, User.display_name)
            .where(
                or_(
                    User.email.ilike(pattern),
                    User.display_name.ilike(pattern),
                )
            )
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        return [
            {"id": r.id, "email": r.email, "display_name": r.display_name}
            for r in self._db.execute(stmt)
        ]

    def search_feedback(
        self, q: str, limit: int, *, include_deleted: bool = False
    ) -> list[dict[str, Any]]:
        pattern = f"%{q}%"
        stmt = (
            select(
                FeedbackTicket.id,
                FeedbackTicket.title,
                FeedbackTicket.status,
            )
            .where(
                or_(
                    FeedbackTicket.title.ilike(pattern),
                    FeedbackTicket.description.ilike(pattern),
                )
            )
            .order_by(FeedbackTicket.created_at.desc())
            .limit(limit)
        )
        if not include_deleted:
            stmt = stmt.where(FeedbackTicket.deleted_at.is_(None))
        return [
            {"id": r.id, "title": r.title, "status": r.status}
            for r in self._db.execute(stmt)
        ]

    def search_announcements(self, q: str, limit: int) -> list[dict[str, Any]]:
        pattern = f"%{q}%"
        rows = list(
            self._db.execute(
                select(Announcement.id, Announcement.title, Announcement.status)
                .where(Announcement.title.ilike(pattern))
                .order_by(Announcement.created_at.desc())
                .limit(limit)
            )
        )
        return [
            {"id": r.id, "title": r.title, "status": r.status} for r in rows
        ]
