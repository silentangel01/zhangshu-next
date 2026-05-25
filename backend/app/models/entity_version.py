from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EntityVersion(Base):
    """Unified version snapshot for non-chapter entities."""

    __tablename__ = "entity_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    entity_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    entity_title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    content_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
