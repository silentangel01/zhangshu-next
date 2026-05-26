"""Cloud backup model for tracking backup uploads."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """Return current UTC+8 time as a naive datetime (SQLite safe)."""
    return datetime.now(_CST).replace(tzinfo=None)


class CloudBackup(Base):
    __tablename__ = "cloud_backups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cloud_projects.id"), nullable=False, index=True
    )
    object_key: Mapped[str] = mapped_column(
        String(512), unique=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="uploading"
    )
    upload_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )
    upload_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
