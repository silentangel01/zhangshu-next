"""Rate limit event model for database-level rate limiting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """Return current UTC+8 time as a naive datetime (SQLite safe)."""
    return datetime.now(_CST).replace(tzinfo=None)


class RateLimitEvent(Base):
    """Tracks rate-limited actions for cross-worker enforcement.

    The ``key`` field stores a hashed or sanitised identifier (never a raw
    email address) so the table does not become a privacy liability.
    """

    __tablename__ = "rate_limit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    scope: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="auth_login | auth_register | backup_init | account_delete",
    )
    key: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
        comment="hashed ip+email or user_id — never raw email",
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    client_ip: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
