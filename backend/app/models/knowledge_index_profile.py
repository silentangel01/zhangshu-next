"""Project-level knowledge index profile model.

Tracks which embedding provider/model/dimension a project currently uses,
ensuring vector consistency across index and retrieval operations.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeIndexProfile(Base):
    """Records the active embedding configuration for a project.

    One profile per project (project_id is unique).
    Updated after a successful index refresh with a new provider.
    """

    __tablename__ = "knowledge_index_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="compat"
    )
    display_name: Mapped[str] = mapped_column(
        String(128), nullable=False, default=""
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    vector_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_size: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ready"
    )
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
