from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WritingStatEvent(Base):
    __tablename__ = "writing_stat_events"
    __table_args__ = (
        Index("ix_writing_stat_events_project_date", "project_id", "local_date"),
        Index(
            "ix_writing_stat_events_project_date_hour",
            "project_id",
            "local_date",
            "local_hour",
        ),
        Index(
            "ix_writing_stat_events_project_chapter_date",
            "project_id",
            "chapter_id",
            "local_date",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    chapter_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    volume_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    old_word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delta_words: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_words: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_words: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    local_date: Mapped[str] = mapped_column(String(10), nullable=False)
    local_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
