"""Feedback attachment model for tracking uploaded files (images/videos)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """Return current UTC+8 time as a naive datetime (SQLite safe)."""
    return datetime.now(_CST).replace(tzinfo=None)


class FeedbackAttachment(Base):
    """Attachment metadata for a feedback ticket."""

    __tablename__ = "feedback_attachments"
    __table_args__ = (
        Index("ix_feedback_att_feedback_status", "feedback_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    feedback_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("feedback_tickets.id"), nullable=False
    )
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="uploading",
        comment="uploading | uploaded | failed | deleted",
    )
    upload_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    upload_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
