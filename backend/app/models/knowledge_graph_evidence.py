from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeGraphEvidence(Base):
    __tablename__ = "knowledge_graph_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("knowledge_graph_entities.id"),
        nullable=True,
        index=True,
    )
    relation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("knowledge_graph_relations.id"),
        nullable=True,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    chunk_heading: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("knowledge_graph_extraction_runs.id"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
