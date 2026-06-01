"""Announcement model for broadcasting notifications to all clients."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """Return current UTC+8 time as a naive datetime (SQLite safe)."""
    return datetime.now(_CST).replace(tzinfo=None)


class Announcement(Base):
    """Developer-published announcement visible to all clients."""

    __tablename__ = "announcements"
    __table_args__ = (
        Index("ix_announcements_status_time", "status", "starts_at", "ends_at"),
        Index("ix_announcements_platform_status", "platform", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(24), nullable=False, default="info",
        comment="info | success | warning | critical",
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="draft",
        comment="draft | published | archived",
    )
    audience: Mapped[str] = mapped_column(
        String(24), nullable=False, default="all",
        comment="v1 only supports 'all'",
    )
    platform: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="windows | macos | linux | null=all",
    )
    min_app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    max_app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
