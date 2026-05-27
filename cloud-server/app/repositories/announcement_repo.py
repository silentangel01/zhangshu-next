"""Announcement data access layer."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.announcement import Announcement
from app.models.user import utc_now


class AnnouncementRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, announcement: Announcement, *, commit: bool = True
    ) -> Announcement:
        self.db.add(announcement)
        if commit:
            self.db.commit()
            self.db.refresh(announcement)
        return announcement

    def get_by_id(self, announcement_id: str) -> Announcement | None:
        return self.db.scalar(
            select(Announcement).where(
                Announcement.id == announcement_id,
                Announcement.deleted_at.is_(None),
            )
        )

    def list_active(
        self,
        now: datetime | None = None,
        platform: str | None = None,
        app_version: str | None = None,
    ) -> list[Announcement]:
        """Return published announcements visible at *now*.

        Filters out drafts, archived, expired, and not-yet-started items.
        Platform filter is applied only when provided.
        ``app_version`` is stored but not used for semver comparison in v1.
        """
        if now is None:
            now = utc_now()

        stmt = (
            select(Announcement)
            .where(
                Announcement.status == "published",
                Announcement.deleted_at.is_(None),
            )
        )

        # Time window: starts_at ≤ now AND (ends_at IS NULL OR ends_at ≥ now)
        stmt = stmt.where(
            (Announcement.starts_at.is_(None)) | (Announcement.starts_at <= now)
        )
        stmt = stmt.where(
            (Announcement.ends_at.is_(None)) | (Announcement.ends_at >= now)
        )

        # Platform filter
        if platform:
            stmt = stmt.where(
                (Announcement.platform.is_(None))
                | (Announcement.platform == platform)
            )

        stmt = stmt.order_by(Announcement.published_at.desc())
        return list(self.db.scalars(stmt).all())

    def count_active(
        self,
        now: datetime | None = None,
        platform: str | None = None,
    ) -> int:
        if now is None:
            now = utc_now()

        subq = (
            select(Announcement)
            .where(
                Announcement.status == "published",
                Announcement.deleted_at.is_(None),
                (Announcement.starts_at.is_(None)) | (Announcement.starts_at <= now),
                (Announcement.ends_at.is_(None)) | (Announcement.ends_at >= now),
            )
        )
        if platform:
            subq = subq.where(
                (Announcement.platform.is_(None))
                | (Announcement.platform == platform)
            )
        stmt = select(func.count()).select_from(subq.subquery())
        return self.db.scalar(stmt) or 0

    def list_admin(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Announcement]:
        stmt = select(Announcement).where(Announcement.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Announcement.status == status)
        stmt = stmt.order_by(Announcement.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_admin(self, status: str | None = None) -> int:
        stmt = select(func.count()).select_from(
            select(Announcement)
            .where(Announcement.deleted_at.is_(None))
            .subquery()
        )
        if status:
            stmt = select(func.count()).select_from(
                select(Announcement)
                .where(
                    Announcement.deleted_at.is_(None),
                    Announcement.status == status,
                )
                .subquery()
            )
        return self.db.scalar(stmt) or 0

    def update(
        self,
        announcement: Announcement,
        values: dict,
        *,
        commit: bool = True,
    ) -> Announcement:
        for key, value in values.items():
            setattr(announcement, key, value)
        announcement.updated_at = utc_now()
        if commit:
            self.db.commit()
            self.db.refresh(announcement)
        return announcement

    def soft_delete(
        self, announcement: Announcement, *, commit: bool = True
    ) -> None:
        announcement.deleted_at = utc_now()
        if commit:
            self.db.commit()
