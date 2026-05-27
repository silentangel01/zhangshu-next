"""User activity event model for admin dashboard metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# UTC+8
_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    return datetime.now(_CST).replace(tzinfo=None)


class UserActivityEvent(Base):
    """Low-sensitivity user behavior events for admin metrics.

    Records events like login, register, backup, feedback — never tokens,
    passwords, presigned URLs, or plaintext IPs.
    """

    __tablename__ = "user_activity_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    client_ip_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
