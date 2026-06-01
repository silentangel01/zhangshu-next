"""Cloud sync snapshot — historical version of a synced entity (FIFO)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CloudSyncSnapshot(Base):
    """Immutable historical snapshot of an entity at a given cloud_version.

    Each ``(project_id, entity_type, entity_id)`` retains at most N snapshots
    (configurable, default 10).  Oldest are pruned after each new insert.
    """

    __tablename__ = "cloud_sync_snapshots"
    __table_args__ = (
        Index(
            "ix_cloud_sync_snapshots_entity",
            "project_id",
            "entity_type",
            "entity_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    cloud_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="push"
    )
    device_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
