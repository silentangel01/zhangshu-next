"""Data access layer for cloud sync tables."""

from __future__ import annotations

import json
import logging

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.cloud_sync_change import CloudSyncChange
from app.models.cloud_sync_conflict import CloudSyncConflict
from app.models.cloud_sync_entity import CloudSyncEntity
from app.models.cloud_sync_snapshot import CloudSyncSnapshot

logger = logging.getLogger(__name__)


class CloudSyncRepo:
    def __init__(self, db: Session):
        self.db = db

    # ── Entity ───────────────────────────────────────────────────

    def get_entity(
        self,
        project_id: str,
        entity_type: str,
        entity_id: str,
    ) -> CloudSyncEntity | None:
        return self.db.scalars(
            select(CloudSyncEntity).where(
                CloudSyncEntity.project_id == project_id,
                CloudSyncEntity.entity_type == entity_type,
                CloudSyncEntity.entity_id == entity_id,
            )
        ).first()

    def upsert_entity(
        self,
        owner_id: str,
        project_id: str,
        entity_type: str,
        entity_id: str,
        cloud_version: int,
        payload_json: str,
        payload_hash: str,
        local_updated_at,
        last_change_id: int,
        deleted: bool = False,
    ) -> CloudSyncEntity:
        entity = self.get_entity(project_id, entity_type, entity_id)
        if entity is None:
            entity = CloudSyncEntity(
                owner_id=owner_id,
                project_id=project_id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            self.db.add(entity)

        entity.cloud_version = cloud_version
        entity.payload_json = payload_json
        entity.payload_hash = payload_hash
        entity.local_updated_at = local_updated_at
        entity.last_change_id = last_change_id
        entity.deleted_at = _utc_now() if deleted else None
        entity.updated_at = _utc_now()
        self.db.flush()
        return entity

    # ── Change log ───────────────────────────────────────────────

    def append_change(
        self,
        owner_id: str,
        project_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        cloud_version: int,
        payload_json: str,
        device_id: str = "",
    ) -> CloudSyncChange:
        change = CloudSyncChange(
            owner_id=owner_id,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            cloud_version=cloud_version,
            payload_json=payload_json,
            device_id=device_id,
        )
        self.db.add(change)
        self.db.flush()
        return change

    def list_changes_after(
        self,
        project_id: str,
        cursor: int,
        limit: int,
    ) -> list[CloudSyncChange]:
        return list(
            self.db.scalars(
                select(CloudSyncChange)
                .where(
                    CloudSyncChange.project_id == project_id,
                    CloudSyncChange.id > cursor,
                )
                .order_by(CloudSyncChange.id.asc())
                .limit(limit)
            ).all()
        )

    def get_latest_change_id(self, project_id: str) -> int:
        result = self.db.scalar(
            select(func.max(CloudSyncChange.id)).where(
                CloudSyncChange.project_id == project_id,
            )
        )
        return result or 0

    # ── Snapshots ────────────────────────────────────────────────

    def create_snapshot(
        self,
        owner_id: str,
        project_id: str,
        entity_type: str,
        entity_id: str,
        cloud_version: int,
        payload_json: str,
        source: str = "push",
        device_id: str = "",
    ) -> CloudSyncSnapshot:
        snap = CloudSyncSnapshot(
            owner_id=owner_id,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            cloud_version=cloud_version,
            payload_json=payload_json,
            source=source,
            device_id=device_id,
        )
        self.db.add(snap)
        self.db.flush()
        return snap

    def prune_snapshots(
        self,
        project_id: str,
        entity_type: str,
        entity_id: str,
        keep: int,
    ) -> int:
        """Delete oldest snapshots beyond *keep* for a given entity.

        Returns the number of deleted rows.
        """
        # Get IDs to keep (most recent)
        keep_ids = [
            row[0]
            for row in self.db.execute(
                select(CloudSyncSnapshot.id)
                .where(
                    CloudSyncSnapshot.project_id == project_id,
                    CloudSyncSnapshot.entity_type == entity_type,
                    CloudSyncSnapshot.entity_id == entity_id,
                )
                .order_by(CloudSyncSnapshot.id.desc())
                .limit(keep)
            ).all()
        ]
        if not keep_ids:
            return 0

        result = self.db.execute(
            delete(CloudSyncSnapshot).where(
                CloudSyncSnapshot.project_id == project_id,
                CloudSyncSnapshot.entity_type == entity_type,
                CloudSyncSnapshot.entity_id == entity_id,
                CloudSyncSnapshot.id.notin_(keep_ids),
            )
        )
        self.db.flush()
        return result.rowcount

    def list_snapshots(
        self,
        project_id: str,
        entity_type: str,
        entity_id: str,
        limit: int = 20,
    ) -> list[CloudSyncSnapshot]:
        return list(
            self.db.scalars(
                select(CloudSyncSnapshot)
                .where(
                    CloudSyncSnapshot.project_id == project_id,
                    CloudSyncSnapshot.entity_type == entity_type,
                    CloudSyncSnapshot.entity_id == entity_id,
                )
                .order_by(CloudSyncSnapshot.id.desc())
                .limit(limit)
            ).all()
        )

    # ── Conflicts ────────────────────────────────────────────────

    def create_conflict(
        self,
        owner_id: str,
        project_id: str,
        entity_type: str,
        entity_id: str,
        winner_payload_json: str,
        loser_payload_json: str,
        winner_source: str = "cloud",
        loser_source: str = "local",
        winner_device_id: str = "",
        loser_device_id: str = "",
    ) -> CloudSyncConflict:
        conflict = CloudSyncConflict(
            owner_id=owner_id,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            winner_payload_json=winner_payload_json,
            loser_payload_json=loser_payload_json,
            winner_source=winner_source,
            loser_source=loser_source,
            winner_device_id=winner_device_id,
            loser_device_id=loser_device_id,
        )
        self.db.add(conflict)
        self.db.flush()
        return conflict

    def list_conflicts(
        self,
        project_id: str,
        resolved: bool | None = False,
        limit: int = 50,
    ) -> list[CloudSyncConflict]:
        stmt = select(CloudSyncConflict).where(
            CloudSyncConflict.project_id == project_id,
        )
        if resolved is not None:
            stmt = stmt.where(CloudSyncConflict.resolved == resolved)
        stmt = stmt.order_by(CloudSyncConflict.id.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())


def _utc_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
