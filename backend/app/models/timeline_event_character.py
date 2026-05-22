from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimelineEventCharacter(Base):
    __tablename__ = "timeline_event_characters"
    __table_args__ = (
        UniqueConstraint(
            "timeline_event_id",
            "character_id",
            name="uq_timeline_event_characters_event_character",
        ),
        Index("ix_timeline_event_characters_project_id", "project_id"),
        Index("ix_timeline_event_characters_event_id", "timeline_event_id"),
        Index("ix_timeline_event_characters_character_id", "character_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    timeline_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    character_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False, default="related")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
