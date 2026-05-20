from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChapterCharacter(Base):
    __tablename__ = "chapter_characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    chapter_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chapters.id"),
        nullable=False,
        index=True,
    )
    character_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("characters.id"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(32), default="appears", nullable=False)
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
