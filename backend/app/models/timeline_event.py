from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), default="plot", nullable=False, index=True)
    story_date: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    story_time: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    importance: Mapped[str] = mapped_column(String(32), default="normal", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False, index=True)
    chapter_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("chapters.id"),
        nullable=True,
        index=True,
    )
    location_setting_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("setting_items.id"),
        nullable=True,
        index=True,
    )
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
