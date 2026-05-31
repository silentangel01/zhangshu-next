"""Cloud sync change log — append-only cursor source for pull."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CloudSyncChange(Base):
    """Append-only change log entry.

    The auto-increment ``id`` serves as the global monotonic cursor for pull.
    Clients query ``id > cursor ORDER BY id LIMIT n`` to receive changes.
    """

    __tablename__ = "cloud_sync_changes"
    __table_args__ = (
        Index(
            "ix_cloud_sync_changes_project_id",
            "project_id",
        ),
        Index(
            "ix_cloud_sync_changes_project_cursor",
            "project_id",
            "id",
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
    action: Mapped[str] = mapped_column(
        String(16), nullable=False, default="upsert"
    )
    cloud_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    device_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
