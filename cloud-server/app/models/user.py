"""User model for cloud service authentication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# UTC+8 — 面向中国用户，存储和显示统一使用北京时间
_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """Return current UTC+8 time as a naive datetime.

    Naive so SQLite round-trips work, but the value is already in Beijing
    time (UTC+8), so it displays correctly to Chinese users.
    """
    return datetime.now(_CST).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    admin_role: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True,
        comment="owner | admin | support | ops | readonly — null for non-admin users",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Privacy / deletion fields
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    anonymized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    privacy_version_accepted: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Profile fields (Phase 1 — 004 migration)
    avatar_object_key: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    avatar_content_type: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )
    avatar_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    signature: Mapped[str | None] = mapped_column(
        String(160), nullable=True
    )

    # Activity tracking fields (Phase 1 — 004 migration)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
