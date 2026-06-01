"""Incremental sync API endpoints."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.sync import (
    SyncConflictListResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncPullResponse,
    SyncSnapshotResponse,
)
from app.services.sync_service import (
    SyncError,
    SyncPayloadTooLargeError,
    SyncTooManyChangesError,
    SyncService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/sync", tags=["sync"])


def _get_sync_service(db: Session = Depends(get_db)) -> SyncService:
    return SyncService(db)


# ── Push ─────────────────────────────────────────────────────────


@router.post("/push", response_model=SyncPushResponse)
def sync_push(
    project_id: str,
    request: SyncPushRequest,
    user: User = Depends(get_current_user),
    service: SyncService = Depends(_get_sync_service),
):
    """Upload local changes to the cloud.

    The client sends a batch of entity changes.  The server applies them,
    detects conflicts (last-write-wins), records snapshots, and returns
    the new cursor position along with accepted/rejected/conflict lists.
    """
    try:
        return service.push(project_id, user.id, request)
    except SyncPayloadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except SyncTooManyChangesError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Pull ─────────────────────────────────────────────────────────


@router.get("/pull", response_model=SyncPullResponse)
def sync_pull(
    project_id: str,
    cursor: int = Query(default=0, ge=0, description="Last known change id"),
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(get_current_user),
    service: SyncService = Depends(_get_sync_service),
):
    """Download cloud changes since *cursor*.

    Returns up to *limit* changes and a ``has_more`` flag.
    """
    try:
        return service.pull(project_id, user.id, cursor, limit)
    except SyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Snapshots ────────────────────────────────────────────────────


@router.get("/snapshots", response_model=list[SyncSnapshotResponse])
def sync_list_snapshots(
    project_id: str,
    entity_type: str = Query(..., min_length=1, max_length=64),
    entity_id: str = Query(..., min_length=1, max_length=36),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: SyncService = Depends(_get_sync_service),
):
    """List historical snapshots for a specific entity."""
    try:
        snapshots = service.list_snapshots(
            project_id, user.id, entity_type, entity_id, limit
        )
        result = []
        for s in snapshots:
            data = None
            try:
                data = json.loads(s.payload_json) if s.payload_json else None
            except (json.JSONDecodeError, TypeError):
                data = None
            result.append(
                SyncSnapshotResponse(
                    id=s.id,
                    entity_type=s.entity_type,
                    entity_id=s.entity_id,
                    cloud_version=s.cloud_version,
                    payload_json=data,
                    source=s.source,
                    device_id=s.device_id,
                    created_at=s.created_at,
                )
            )
        return result
    except SyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Conflicts ────────────────────────────────────────────────────


@router.get("/conflicts", response_model=list[SyncConflictListResponse])
def sync_list_conflicts(
    project_id: str,
    resolved: bool | None = Query(default=False),
    user: User = Depends(get_current_user),
    service: SyncService = Depends(_get_sync_service),
):
    """List sync conflicts for a project."""
    try:
        conflicts = service.list_conflicts(project_id, user.id, resolved)
        result = []
        for c in conflicts:
            winner_data = None
            loser_data = None
            try:
                winner_data = json.loads(c.winner_payload_json) if c.winner_payload_json else None
            except (json.JSONDecodeError, TypeError):
                pass
            try:
                loser_data = json.loads(c.loser_payload_json) if c.loser_payload_json else None
            except (json.JSONDecodeError, TypeError):
                pass
            result.append(
                SyncConflictListResponse(
                    id=c.id,
                    entity_type=c.entity_type,
                    entity_id=c.entity_id,
                    winner_payload_json=winner_data,
                    loser_payload_json=loser_data,
                    winner_source=c.winner_source,
                    loser_source=c.loser_source,
                    resolved=c.resolved,
                    created_at=c.created_at,
                )
            )
        return result
    except SyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
