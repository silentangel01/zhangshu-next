"""Account deletion request model for two-stage safe deletion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """Return current UTC+8 time as a naive datetime (SQLite safe)."""
    return datetime.now(_CST).replace(tzinfo=None)


class AccountDeletionRequest(Base):
    """Stores a pending account deletion confirmation.

    The ``confirm_token_hash`` is a SHA-256 hash of a random token sent to
    the client.  The plain token is never persisted.
    """

    __tablename__ = "account_deletion_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    confirm_token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    summary_json: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment='JSON snapshot: project_count, backup_count, total_size_bytes',
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
