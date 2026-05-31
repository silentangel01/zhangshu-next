"""Business logic for the incremental sync API."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.cloud_project_repo import CloudProjectRepository
from app.repositories.cloud_sync_repo import CloudSyncRepo
from app.schemas.sync import (
    SyncAcceptedChange,
    SyncChangeIn,
    SyncChangeOut,
    SyncConflictResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncPullResponse,
    SyncRejectedChange,
)

logger = logging.getLogger(__name__)

# P0/P1 entity types supported for incremental sync (L1 + L2 + L3)
ALLOWED_ENTITY_TYPES: set[str] = {
    # P0 entities
    "projects",
    "volumes",
    "chapters",
    "characters",
    "setting_items",
    "clues",
    "outline_items",
    "timeline_tracks",
    "timeline_events",
    "timeline_edges",
    "graph_nodes",
    "graph_edges",
    # P1 join entities
    "chapter_characters",
    "chapter_settings",
    "chapter_clues",
    "clue_characters",
    "clue_settings",
    "timeline_event_characters",
    "timeline_event_settings",
    "timeline_event_clues",
    "outline_item_characters",
    "outline_item_settings",
    "outline_item_clues",
    "outline_item_timeline_events",
}


class SyncError(Exception):
    """Base class for sync-related errors."""


class SyncEntityTypeError(SyncError):
    """Entity type not in the allowed list."""


class SyncPayloadTooLargeError(SyncError):
    """Request payload exceeds the configured byte limit."""


class SyncTooManyChangesError(SyncError):
    """Number of changes in a single push exceeds the limit."""


def _canonical_json(obj: dict | None) -> str:
    """Deterministic JSON encoding for stable hashing."""
    if obj is None:
        return "{}"
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _payload_hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _parse_utc(value: datetime | str | None) -> datetime:
    """Parse a datetime or ISO string into a timezone-aware UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


class SyncService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CloudSyncRepo(db)
        self.project_repo = CloudProjectRepository(db)
        self.settings = get_settings()

    def _check_project_owner(self, project_id: str, user_id: str) -> None:
        project = self.project_repo.get_by_id(project_id)
        if project is None or project.deleted_at is not None:
            raise SyncError("项目不存在。")
        if project.owner_id != user_id:
            raise SyncError("无权访问该项目。")

    def _check_entity_type(self, entity_type: str) -> None:
        if entity_type not in ALLOWED_ENTITY_TYPES:
            raise SyncEntityTypeError(
                f"不支持的实体类型: {entity_type}。"
                f"当前支持的实体类型: {', '.join(sorted(ALLOWED_ENTITY_TYPES))}"
            )

    # ── Push ─────────────────────────────────────────────────────

    def push(
        self, project_id: str, user_id: str, request: SyncPushRequest
    ) -> SyncPushResponse:
        self._check_project_owner(project_id, user_id)

        max_changes = self.settings.sync_max_changes_per_request
        if len(request.changes) > max_changes:
            raise SyncTooManyChangesError(
                f"单次 push 最多 {max_changes} 条变更，"
                f"当前 {len(request.changes)} 条。"
            )

        # Check total payload size (approximate)
        max_bytes = self.settings.sync_max_payload_bytes
        total_bytes = sum(
            len(_canonical_json(c.data)) for c in request.changes if c.data
        )
        if total_bytes > max_bytes:
            raise SyncPayloadTooLargeError(
                f"请求体超过限制 ({max_bytes} bytes)，当前约 {total_bytes} bytes。"
            )

        accepted: list[SyncAcceptedChange] = []
        rejected: list[SyncRejectedChange] = []
        conflicts: list[SyncConflictResponse] = []

        for change in request.changes:
            try:
                result = self._apply_change(project_id, user_id, change)
                if result["status"] == "accepted":
                    accepted.append(
                        SyncAcceptedChange(
                            entity_type=change.entity_type,
                            entity_id=change.entity_id,
                            cloud_version=result["cloud_version"],
                            change_id=result["change_id"],
                        )
                    )
                elif result["status"] == "conflict":
                    # LWW: the push still wins in L1 MVP, but we record the conflict
                    accepted.append(
                        SyncAcceptedChange(
                            entity_type=change.entity_type,
                            entity_id=change.entity_id,
                            cloud_version=result["cloud_version"],
                            change_id=result["change_id"],
                        )
                    )
                    conflicts.append(
                        SyncConflictResponse(
                            entity_type=change.entity_type,
                            entity_id=change.entity_id,
                            cloud_version=result["cloud_version"],
                            cloud_data=result.get("prev_data"),
                            local_version=change.local_version,
                            winner="local",
                        )
                    )
            except SyncEntityTypeError as exc:
                rejected.append(
                    SyncRejectedChange(
                        entity_type=change.entity_type,
                        entity_id=change.entity_id,
                        reason=str(exc),
                    )
                )

        self.db.commit()
        new_cursor = self.repo.get_latest_change_id(project_id)

        return SyncPushResponse(
            new_cursor=new_cursor,
            accepted=accepted,
            rejected=rejected,
            conflicts=conflicts,
        )

    def _apply_change(
        self,
        project_id: str,
        user_id: str,
        change: SyncChangeIn,
    ) -> dict:
        self._check_entity_type(change.entity_type)

        payload_str = _canonical_json(change.data)
        p_hash = _payload_hash(payload_str)
        local_updated = _parse_utc(change.local_updated_at)

        existing = self.repo.get_entity(
            project_id, change.entity_type, change.entity_id
        )

        is_conflict = False
        prev_data = None

        if existing is not None:
            # Conflict check: client's base_cloud_version < current cloud_version
            if change.base_cloud_version < existing.cloud_version:
                is_conflict = True
                prev_data = json.loads(existing.payload_json) if existing.payload_json else None

                # L1 MVP LWW: compare local_updated_at with entity's local_updated_at
                existing_local_ts = _parse_utc(existing.local_updated_at)
                if local_updated <= existing_local_ts:
                    # Cloud wins: skip this push, create snapshot/conflict of the loser
                    self.repo.create_snapshot(
                        owner_id=user_id,
                        project_id=project_id,
                        entity_type=change.entity_type,
                        entity_id=change.entity_id,
                        cloud_version=existing.cloud_version,
                        payload_json=payload_str,
                        source="conflict_loser",
                        device_id=change.device_id,
                    )
                    self.repo.create_conflict(
                        owner_id=user_id,
                        project_id=project_id,
                        entity_type=change.entity_type,
                        entity_id=change.entity_id,
                        winner_payload_json=existing.payload_json,
                        loser_payload_json=payload_str,
                        winner_source="cloud",
                        loser_source="local",
                        winner_device_id="",
                        loser_device_id=change.device_id,
                    )
                    # Return as conflict (not accepted)
                    return {
                        "status": "conflict",
                        "cloud_version": existing.cloud_version,
                        "change_id": existing.last_change_id,
                        "prev_data": prev_data,
                    }

            new_version = existing.cloud_version + 1
        else:
            new_version = 1

        # Apply the change
        deleted = change.action == "delete"
        entity = self.repo.upsert_entity(
            owner_id=user_id,
            project_id=project_id,
            entity_type=change.entity_type,
            entity_id=change.entity_id,
            cloud_version=new_version,
            payload_json=payload_str,
            payload_hash=p_hash,
            local_updated_at=local_updated,
            last_change_id=0,  # will be updated after append_change
            deleted=deleted,
        )

        change_record = self.repo.append_change(
            owner_id=user_id,
            project_id=project_id,
            entity_type=change.entity_type,
            entity_id=change.entity_id,
            action=change.action,
            cloud_version=new_version,
            payload_json=payload_str,
            device_id=change.device_id,
        )

        entity.last_change_id = change_record.id
        self.db.flush()

        # Create snapshot and prune
        self.repo.create_snapshot(
            owner_id=user_id,
            project_id=project_id,
            entity_type=change.entity_type,
            entity_id=change.entity_id,
            cloud_version=new_version,
            payload_json=payload_str,
            source="push",
            device_id=change.device_id,
        )
        self.repo.prune_snapshots(
            project_id=project_id,
            entity_type=change.entity_type,
            entity_id=change.entity_id,
            keep=self.settings.sync_snapshot_retention_per_entity,
        )

        status = "conflict" if is_conflict else "accepted"
        return {
            "status": status,
            "cloud_version": new_version,
            "change_id": change_record.id,
            "prev_data": prev_data,
        }

    # ── Pull ─────────────────────────────────────────────────────

    def pull(
        self,
        project_id: str,
        user_id: str,
        cursor: int = 0,
        limit: int | None = None,
    ) -> SyncPullResponse:
        self._check_project_owner(project_id, user_id)

        if limit is None:
            limit = self.settings.sync_max_changes_per_request
        limit = min(limit, self.settings.sync_max_changes_per_request)

        # Fetch limit+1 to detect has_more
        raw_changes = self.repo.list_changes_after(project_id, cursor, limit + 1)
        has_more = len(raw_changes) > limit
        if has_more:
            raw_changes = raw_changes[:limit]

        changes: list[SyncChangeOut] = []
        for ch in raw_changes:
            data = None
            try:
                data = json.loads(ch.payload_json) if ch.payload_json else None
            except (json.JSONDecodeError, TypeError):
                data = None

            changes.append(
                SyncChangeOut(
                    change_id=ch.id,
                    entity_type=ch.entity_type,
                    entity_id=ch.entity_id,
                    action=ch.action,
                    cloud_version=ch.cloud_version,
                    data=data,
                    device_id=ch.device_id,
                    created_at=ch.created_at,
                )
            )

        new_cursor = changes[-1].change_id if changes else cursor

        return SyncPullResponse(
            new_cursor=new_cursor,
            changes=changes,
            has_more=has_more,
        )

    # ── Snapshots / Conflicts (read-only) ────────────────────────

    def list_snapshots(
        self,
        project_id: str,
        user_id: str,
        entity_type: str,
        entity_id: str,
        limit: int = 20,
    ):
        self._check_project_owner(project_id, user_id)
        self._check_entity_type(entity_type)
        return self.repo.list_snapshots(project_id, entity_type, entity_id, limit)

    def list_conflicts(
        self,
        project_id: str,
        user_id: str,
        resolved: bool | None = False,
    ):
        self._check_project_owner(project_id, user_id)
        return self.repo.list_conflicts(project_id, resolved)
