"""Sync dirty service — tracks locally modified entities pending cloud upload."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.sync_dirty_record import SyncDirtyRecord

logger = logging.getLogger(__name__)

_VALID_ACTIONS = {"upsert", "delete"}


class SyncDirtyService:
    """Manages dirty records that need to be pushed to the cloud."""

    def __init__(self, db: Session):
        self.db = db

    def mark_dirty(
        self,
        project_id: str,
        entity_type: str,
        entity_id: str,
        action: str = "upsert",
    ) -> SyncDirtyRecord:
        """Mark an entity as dirty (needing cloud upload).

        If a dirty record already exists for the same entity, update its
        action and updated_at. This is an upsert on (project_id, entity_type, entity_id).
        """
        if action not in _VALID_ACTIONS:
            raise ValueError(f"Invalid dirty action: {action}. Must be one of {_VALID_ACTIONS}")

        now = datetime.now(timezone.utc)

        # Check for existing record
        existing = (
            self.db.query(SyncDirtyRecord)
            .filter(
                SyncDirtyRecord.project_id == project_id,
                SyncDirtyRecord.entity_type == entity_type,
                SyncDirtyRecord.entity_id == entity_id,
            )
            .first()
        )

        if existing is not None:
            existing.action = action
            existing.updated_at = now
            existing.last_error = None
            self.db.commit()
            self.db.refresh(existing)
            return existing

        record = SyncDirtyRecord(
            id=str(uuid4()),
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_dirty(self, project_id: str, limit: int = 200) -> list[SyncDirtyRecord]:
        """List all dirty records for a project, ordered by creation time."""
        return (
            self.db.query(SyncDirtyRecord)
            .filter(SyncDirtyRecord.project_id == project_id)
            .order_by(SyncDirtyRecord.created_at.asc())
            .limit(limit)
            .all()
        )

    def count_dirty(self, project_id: str) -> int:
        """Count dirty records for a project."""
        return (
            self.db.query(SyncDirtyRecord)
            .filter(SyncDirtyRecord.project_id == project_id)
            .count()
        )

    def remove_dirty(
        self,
        project_id: str,
        entity_type: str,
        entity_id: str,
    ) -> None:
        """Remove a specific dirty record (after successful push)."""
        self.db.query(SyncDirtyRecord).filter(
            SyncDirtyRecord.project_id == project_id,
            SyncDirtyRecord.entity_type == entity_type,
            SyncDirtyRecord.entity_id == entity_id,
        ).delete()
        self.db.commit()

    def remove_dirty_batch(
        self,
        project_id: str,
        entities: list[tuple[str, str]],
    ) -> int:
        """Remove multiple dirty records. Returns count deleted.

        ``entities`` is a list of ``(entity_type, entity_id)`` tuples.
        """
        if not entities:
            return 0

        deleted = 0
        for entity_type, entity_id in entities:
            count = (
                self.db.query(SyncDirtyRecord)
                .filter(
                    SyncDirtyRecord.project_id == project_id,
                    SyncDirtyRecord.entity_type == entity_type,
                    SyncDirtyRecord.entity_id == entity_id,
                )
                .delete()
            )
            deleted += count
        self.db.commit()
        return deleted

    def mark_error(
        self,
        project_id: str,
        entity_type: str,
        entity_id: str,
        error: str,
    ) -> None:
        """Record an error on a dirty record and increment attempt count."""
        record = (
            self.db.query(SyncDirtyRecord)
            .filter(
                SyncDirtyRecord.project_id == project_id,
                SyncDirtyRecord.entity_type == entity_type,
                SyncDirtyRecord.entity_id == entity_id,
            )
            .first()
        )
        if record is not None:
            record.attempt_count += 1
            record.last_error = error
            record.updated_at = datetime.now(timezone.utc)
            self.db.commit()
