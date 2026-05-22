from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OutlineItemCharacter(Base):
    __tablename__ = "outline_item_characters"
    __table_args__ = (
        UniqueConstraint(
            "outline_item_id",
            "character_id",
            name="uq_outline_item_characters_outline_character",
        ),
        Index("ix_outline_item_characters_project_id", "project_id"),
        Index("ix_outline_item_characters_outline_item_id", "outline_item_id"),
        Index("ix_outline_item_characters_character_id", "character_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    outline_item_id: Mapped[str] = mapped_column(String(36), nullable=False)
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
