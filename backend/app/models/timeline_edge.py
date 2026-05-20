from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimelineEdge(Base):
    __tablename__ = "timeline_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    from_event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("timeline_events.id"),
        nullable=False,
        index=True,
    )
    to_event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("timeline_events.id"),
        nullable=False,
        index=True,
    )
    edge_type: Mapped[str] = mapped_column(String(32), default="related", nullable=False, index=True)
    line_style: Mapped[str] = mapped_column(String(32), default="straight", nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="normal", nullable=False, index=True)
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
