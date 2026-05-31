"""Local cloud sync state — tracks sync cursor and status per project."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CloudSyncState(Base):
    """Tracks incremental sync state for a local project linked to a cloud project.

    One row per ``(project_id, cloud_user_id)`` — the unique constraint ensures
    the same user cannot have duplicate sync states for the same project.
    """

    __tablename__ = "cloud_sync_states"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "cloud_user_id",
            name="uq_cloud_sync_states_project_user",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cloud_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cloud_project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    last_cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="idle"
    )
    auto_sync_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
