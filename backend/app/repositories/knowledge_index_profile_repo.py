"""Repository for knowledge index profile CRUD operations."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_index_profile import KnowledgeIndexProfile


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeIndexProfileRepository:
    """Manages persistence of project-level embedding profiles."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_project(self, project_id: str) -> KnowledgeIndexProfile | None:
        """Return the profile for a project, or None if not found."""
        stmt = select(KnowledgeIndexProfile).where(
            KnowledgeIndexProfile.project_id == project_id
        )
        return self.db.scalar(stmt)

    def upsert(
        self,
        project_id: str,
        provider_id: str,
        model_name: str,
        vector_dim: int,
        provider_type: str = "compat",
        display_name: str = "",
        chunk_size: str = "medium",
        status: str = "ready",
        last_refreshed_at: datetime | None = None,
        last_error: str | None = None,
    ) -> KnowledgeIndexProfile:
        """Create or update the profile for a project.

        Returns the persisted profile.
        """
        existing = self.get_by_project(project_id)
        now = utc_now()

        if existing:
            existing.provider_id = provider_id
            existing.provider_type = provider_type
            existing.display_name = display_name
            existing.model_name = model_name
            existing.vector_dim = vector_dim
            existing.chunk_size = chunk_size
            existing.status = status
            existing.last_refreshed_at = last_refreshed_at
            existing.last_error = last_error
            existing.updated_at = now
            self.db.commit()
            self.db.refresh(existing)
            return existing

        profile = KnowledgeIndexProfile(
            id=str(uuid4()),
            project_id=project_id,
            provider_id=provider_id,
            provider_type=provider_type,
            display_name=display_name,
            model_name=model_name,
            vector_dim=vector_dim,
            chunk_size=chunk_size,
            status=status,
            last_refreshed_at=last_refreshed_at,
            last_error=last_error,
            created_at=now,
            updated_at=now,
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def mark_error(self, project_id: str, error_message: str) -> None:
        """Mark a profile as errored with a short error description."""
        existing = self.get_by_project(project_id)
        if existing is None:
            return
        existing.status = "error"
        existing.last_error = error_message[:500]
        existing.updated_at = utc_now()
        self.db.commit()

    def mark_stale(self, project_id: str) -> None:
        """Mark a profile as stale (e.g. after source content changes)."""
        existing = self.get_by_project(project_id)
        if existing is None:
            return
        existing.status = "stale"
        existing.updated_at = utc_now()
        self.db.commit()
