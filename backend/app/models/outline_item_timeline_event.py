from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OutlineItemTimelineEvent(Base):
    __tablename__ = "outline_item_timeline_events"
    __table_args__ = (
        UniqueConstraint(
            "outline_item_id",
            "timeline_event_id",
            name="uq_outline_item_timeline_events_outline_event",
        ),
        Index("ix_outline_item_timeline_events_project_id", "project_id"),
        Index("ix_outline_item_timeline_events_outline_item_id", "outline_item_id"),
        Index("ix_outline_item_timeline_events_event_id", "timeline_event_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    outline_item_id: Mapped[str] = mapped_column(String(36), nullable=False)
    timeline_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
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
