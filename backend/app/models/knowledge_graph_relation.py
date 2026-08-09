from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeGraphRelation(Base):
    __tablename__ = "knowledge_graph_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    subject_entity_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_graph_entities.id"),
        nullable=False,
        index=True,
    )
    object_entity_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_graph_entities.id"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(
        String(32),
        default="custom",
        nullable=False,
        index=True,
    )
    predicate_text: Mapped[str] = mapped_column(
        String(255),
        default="",
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(
        String(32),
        default="directed",
        nullable=False,
        index=True,
    )
    fact_status: Mapped[str] = mapped_column(
        String(32),
        default="confirmed",
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="candidate",
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
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
