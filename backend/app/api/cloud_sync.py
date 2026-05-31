"""Cloud incremental sync API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.cloud_api_client import CloudApiNotConfiguredError
from app.infrastructure.database import get_db
from app.schemas.cloud_sync import (
    CloudProjectImportResult,
    CloudSyncConflictItem,
    CloudSyncRunRequest,
    CloudSyncRunResult,
    CloudSyncSnapshotItem,
    CloudSyncStatusResponse,
)
from app.services.cloud_auth_service import CloudAuthError, CloudAuthService
from app.services.cloud_sync_service import CloudSyncError, CloudSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["cloud-sync"])


# ── Dependencies ──────────────────────────────────────────────────


def get_cloud_sync_service(db: Session = Depends(get_db)) -> CloudSyncService:
    return CloudSyncService(db)


# ── Project sync status/run/pull ─────────────────────────────────


@router.get(
    "/projects/{project_id}/cloud/sync/status",
    response_model=CloudSyncStatusResponse,
)
def get_sync_status(
    project_id: str,
    svc: CloudSyncService = Depends(get_cloud_sync_service),
):
    """Get sync status for a project."""
    try:
        return svc.get_status(project_id)
    except CloudSyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post(
    "/projects/{project_id}/cloud/sync/run",
    response_model=CloudSyncRunResult,
)
def run_sync(
    project_id: str,
    body: CloudSyncRunRequest | None = None,
    svc: CloudSyncService = Depends(get_cloud_sync_service),
):
    """Execute a full sync cycle: push dirty records, then pull remote changes."""
    try:
        return svc.run_sync(project_id)
    except CloudSyncError as exc:
        detail = {"detail": str(exc)}
        if exc.error_kind:
            detail["error_kind"] = exc.error_kind
        if exc.suggestion:
            detail["suggestion"] = exc.suggestion
        raise HTTPException(status_code=400, detail=detail)
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "detail": str(exc),
                "error_kind": exc.error_kind,
                "suggestion": exc.suggestion,
            },
        )
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post(
    "/projects/{project_id}/cloud/sync/pull",
    response_model=CloudSyncRunResult,
)
def pull_sync(
    project_id: str,
    svc: CloudSyncService = Depends(get_cloud_sync_service),
):
    """Pull remote changes without pushing local dirty records."""
    try:
        result = svc.pull_only(project_id)
        return CloudSyncRunResult(
            pushed=0,
            pulled=result["pulled"],
            new_cursor=result["new_cursor"],
            conflicts=0,
            errors=result["errors"],
            duration_ms=0,
        )
    except CloudSyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except CloudAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ── Snapshots and conflicts ──────────────────────────────────────


@router.get(
    "/projects/{project_id}/cloud/sync/snapshots",
    response_model=list[CloudSyncSnapshotItem],
)
def list_sync_snapshots(
    project_id: str,
    entity_type: str = Query(..., description="Entity type (e.g. chapters)"),
    entity_id: str = Query(..., description="Entity ID"),
    svc: CloudSyncService = Depends(get_cloud_sync_service),
):
    """List cloud snapshots for a specific entity."""
    try:
        return svc.list_snapshots(project_id, entity_type, entity_id)
    except CloudSyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except CloudAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get(
    "/projects/{project_id}/cloud/sync/conflicts",
    response_model=list[CloudSyncConflictItem],
)
def list_sync_conflicts(
    project_id: str,
    resolved: bool = Query(False, description="Include resolved conflicts"),
    svc: CloudSyncService = Depends(get_cloud_sync_service),
):
    """List cloud conflicts for a project."""
    try:
        return svc.list_conflicts(project_id, resolved)
    except CloudSyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except CloudAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ── Cloud project listing and import ─────────────────────────────


@router.get("/cloud/projects")
def list_cloud_projects(
    db: Session = Depends(get_db),
):
    """List remote cloud projects available for import."""
    auth_svc = CloudAuthService(db)
    if not auth_svc.is_logged_in():
        raise HTTPException(
            status_code=401,
            detail="未登录云账户，请先登录。",
        )
    try:
        result = auth_svc.call_with_refresh(lambda client: client.get_cloud_projects())
    except CloudAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Annotate with local link status
    from app.repositories.cloud_project_link_repo import CloudProjectLinkRepository
    link_repo = CloudProjectLinkRepository(db)
    cloud_user_id = auth_svc.get_cloud_user_id() or ""

    def _annotate(item: dict) -> dict:
        link = link_repo.get_by_cloud_project(item["id"], cloud_user_id)
        if link is not None:
            item["linked_locally"] = True
            item["local_project_id"] = link.project_id
        else:
            item["linked_locally"] = False
            item["local_project_id"] = None
        return item

    if isinstance(result, dict) and "items" in result:
        result["items"] = [_annotate(p) for p in result["items"]]
    elif isinstance(result, list):
        result = [_annotate(p) for p in result]

    return result


@router.post(
    "/cloud/projects/{cloud_project_id}/import",
    response_model=CloudProjectImportResult,
)
def import_cloud_project(
    cloud_project_id: str,
    svc: CloudSyncService = Depends(get_cloud_sync_service),
):
    """Import a cloud project to the local database."""
    try:
        return svc.import_cloud_project(cloud_project_id)
    except CloudSyncError as exc:
        detail = {"detail": str(exc)}
        if exc.error_kind:
            detail["error_kind"] = exc.error_kind
        if exc.suggestion:
            detail["suggestion"] = exc.suggestion
        raise HTTPException(status_code=400, detail=detail)
    except CloudAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
