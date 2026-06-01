"""Audit log model — persistent structured audit trail."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """Return current UTC+8 time as a naive datetime (SQLite safe)."""
    return datetime.now(_CST).replace(tzinfo=None)


class AuditLog(Base):
    """Persisted audit log entry.

    Each row records a single auditable event (login, backup, admin action, etc.)
    with structured fields for filtering and reporting.
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    event: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Event type: login_success, backup_init, admin_toggle_active, ...",
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    client_ip: Mapped[str] = mapped_column(String(45), nullable=False, default="")
    user_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default="", index=True,
    )
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    backup_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    result: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="success",
        comment="success | failure | error",
    )
    reason_code: Mapped[str] = mapped_column(
        String(32), nullable=False, default="",
        comment="Machine-readable failure reason",
    )
    extra_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON-encoded non-sensitive extra fields",
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True,
        comment="Admin user who performed the action",
    )
    target_user_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True,
        comment="User affected by the action (if applicable)",
    )
    client_ip_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="SHA-256 prefix of the client IP for correlation",
    )
    client_ip_masked: Mapped[str | None] = mapped_column(
        String(45), nullable=True,
        comment="Masked IP for display (e.g. 192.168.1.xxx)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_logs_event_created", "event", "created_at"),
    )
