"""Cloud sync entity — latest state of each synced entity per project."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CloudSyncEntity(Base):
    """Current state of a single synced entity within a cloud project.

    Unique on ``(project_id, entity_type, entity_id)`` — one row per logical
    entity.  ``cloud_version`` is monotonically bumped on every accepted push.
    """

    __tablename__ = "cloud_sync_entities"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "entity_type",
            "entity_id",
            name="uq_cloud_sync_entities_project_type_id",
        ),
        Index(
            "ix_cloud_sync_entities_owner_project_type",
            "owner_id",
            "project_id",
            "entity_type",
        ),
        Index(
            "ix_cloud_sync_entities_project_change",
            "project_id",
            "last_change_id",
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
    cloud_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    local_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    last_change_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
