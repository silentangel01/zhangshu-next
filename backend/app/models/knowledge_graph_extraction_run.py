from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeGraphExtractionRun(Base):
    __tablename__ = "knowledge_graph_extraction_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(32), default="source", nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_entity_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_relation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
