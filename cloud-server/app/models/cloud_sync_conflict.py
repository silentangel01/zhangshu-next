"""Cloud sync conflict — record of concurrent write collision."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CloudSyncConflict(Base):
    """Audit record created when a push conflicts with existing cloud state.

    Both the *winner* and *loser* payloads are preserved so no data is lost.
    L1 MVP does not provide a resolution UI — conflicts are just recorded.
    """

    __tablename__ = "cloud_sync_conflicts"
    __table_args__ = (
        Index(
            "ix_cloud_sync_conflicts_project_entity",
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
    winner_payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    loser_payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    winner_source: Mapped[str] = mapped_column(String(32), nullable=False, default="cloud")
    loser_source: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    winner_device_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    loser_device_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
