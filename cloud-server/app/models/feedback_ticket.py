"""Feedback ticket model for user-submitted bug reports and suggestions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """Return current UTC+8 time as a naive datetime (SQLite safe)."""
    return datetime.now(_CST).replace(tzinfo=None)


class FeedbackTicket(Base):
    """User-submitted feedback (bug report, suggestion, etc.)."""

    __tablename__ = "feedback_tickets"
    __table_args__ = (
        Index("ix_feedback_user_created", "user_id", "created_at"),
        Index("ix_feedback_status_created", "status", "created_at"),
        Index("ix_feedback_category_created", "category", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="bug | suggestion | data_loss | cloud | ui | other",
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="open",
        comment="open | triaged | in_progress | closed | spam",
    )
    priority: Mapped[str | None] = mapped_column(
        String(16), nullable=True,
        comment="low | normal | high | urgent",
    )
    app_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    network_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    client_diagnostics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_size_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
