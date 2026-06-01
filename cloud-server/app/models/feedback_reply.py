"""Feedback reply model for admin responses to user feedback."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """Return current UTC+8 time as a naive datetime (SQLite safe)."""
    return datetime.now(_CST).replace(tzinfo=None)


class FeedbackReply(Base):
    """Admin reply to a feedback ticket."""

    __tablename__ = "feedback_replies"
    __table_args__ = (
        Index("ix_feedback_replies_ticket_created", "ticket_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("feedback_tickets.id"), nullable=False
    )
    author_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    author_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="admin",
        comment="admin | system",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
