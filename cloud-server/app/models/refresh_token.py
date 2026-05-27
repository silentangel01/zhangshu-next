"""Refresh token model for JWT token management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """Return current UTC+8 time as a naive datetime (SQLite safe)."""
    return datetime.now(_CST).replace(tzinfo=None)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    jti_hash: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    replaced_by_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )

    # Session tracking fields
    user_agent: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    client_ip: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_reason: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
