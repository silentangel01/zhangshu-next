from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeGraphEntity(Base):
    __tablename__ = "knowledge_graph_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    canonical_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(32),
        default="custom",
        nullable=False,
        index=True,
    )
    aliases_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    bound_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    bound_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="candidate",
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
