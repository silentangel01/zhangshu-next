"""Sync dirty record — tracks locally modified entities pending cloud upload."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SyncDirtyRecord(Base):
    """Records a locally modified entity that needs to be pushed to the cloud.

    Unique on ``(project_id, entity_type, entity_id)`` — repeated edits to the
    same entity just bump ``updated_at`` and update ``action`` if needed.
    """

    __tablename__ = "sync_dirty_records"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "entity_type",
            "entity_id",
            name="uq_sync_dirty_records_project_type_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(
        String(16), nullable=False, default="upsert"
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
