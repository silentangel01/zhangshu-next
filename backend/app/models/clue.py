from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Clue(Base):
    __tablename__ = "clues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    setup_chapter_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("chapters.id"),
        nullable=True,
        index=True,
    )
    payoff_chapter_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("chapters.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False, index=True)
    visibility: Mapped[str] = mapped_column(String(32), default="hidden", nullable=False, index=True)
    importance: Mapped[str] = mapped_column(String(32), default="normal", nullable=False, index=True)
    payoff_plan: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actual_payoff: Mapped[str] = mapped_column(Text, default="", nullable=False)
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
