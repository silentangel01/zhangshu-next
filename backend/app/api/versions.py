from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.version import (
    CleanupVersionsResponse,
    CreateVersionSnapshotRequest,
    RestoreVersionResponse,
    UpdateVersionRequest,
    VersionCompareRequest,
    VersionCompareResponse,
    VersionDetail,
    VersionListItem,
    VersionListResponse,
    VersionSnapshotTargetsResponse,
    VersionSummaryResponse,
)
from app.services.version_service import (
    VersionEntityNotFoundError,
    VersionNotFoundError,
    VersionPinnedError,
    VersionProjectNotFoundError,
    VersionRestoreMismatchError,
    VersionService,
)


router = APIRouter(prefix="/api/projects", tags=["versions"])


def get_version_service(db: Session = Depends(get_db)) -> VersionService:
    return VersionService(db)


@router.get("/{project_id}/versions", response_model=VersionListResponse)
def list_versions(
    project_id: str,
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    source: str | None = Query(default=None),
    pinned: bool | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: VersionService = Depends(get_version_service),
):
    try:
        return service.list_versions(
            project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            source=source,
            pinned=pinned,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
    except VersionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="项目不存在") from exc


# Static POST routes MUST be before {version_ref:path} wildcard routes
@router.post("/{project_id}/versions/snapshots", response_model=VersionListItem)
def create_snapshot(
    project_id: str,
    data: CreateVersionSnapshotRequest,
    service: VersionService = Depends(get_version_service),
):
    try:
        return service.create_snapshot(project_id, data)
    except VersionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="项目不存在") from exc
    except VersionEntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="实体不存在") from exc


@router.post("/{project_id}/versions/compare", response_model=VersionCompareResponse)
def compare_versions(
    project_id: str,
    data: VersionCompareRequest,
    service: VersionService = Depends(get_version_service),
):
    try:
        return service.compare(project_id, data)
    except VersionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="项目不存在") from exc
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="版本不存在") from exc


@router.post("/{project_id}/versions/cleanup", response_model=CleanupVersionsResponse)
def cleanup_versions(
    project_id: str,
    keep_days: int = Query(default=30, ge=1, le=365),
    source: str | None = Query(default=None),
    service: VersionService = Depends(get_version_service),
):
    try:
        return service.cleanup(project_id, keep_days=keep_days, source=source)
    except VersionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="项目不存在") from exc


@router.get("/{project_id}/versions/summary", response_model=VersionSummaryResponse)
def get_version_summary(
    project_id: str,
    service: VersionService = Depends(get_version_service),
):
    try:
        return service.get_summary(project_id)
    except VersionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="项目不存在") from exc


@router.get(
    "/{project_id}/versions/snapshot-targets",
    response_model=VersionSnapshotTargetsResponse,
)
def list_snapshot_targets(
    project_id: str,
    entity_type: str | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    service: VersionService = Depends(get_version_service),
):
    try:
        return service.list_snapshot_targets(
            project_id, entity_type=entity_type, keyword=keyword, limit=limit
        )
    except VersionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="项目不存在") from exc


# Wildcard {version_ref:path} routes — must come AFTER all static sub-paths
@router.get("/{project_id}/versions/{version_ref:path}", response_model=VersionDetail)
def get_version(
    project_id: str,
    version_ref: str,
    service: VersionService = Depends(get_version_service),
):
    try:
        return service.get_version(project_id, version_ref)
    except VersionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="项目不存在") from exc
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="版本不存在") from exc


@router.patch("/{project_id}/versions/{version_ref:path}", response_model=VersionListItem)
def update_version(
    project_id: str,
    version_ref: str,
    data: UpdateVersionRequest,
    service: VersionService = Depends(get_version_service),
):
    try:
        return service.update_version(project_id, version_ref, data)
    except VersionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="项目不存在") from exc
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="版本不存在") from exc


@router.delete("/{project_id}/versions/{version_ref:path}", status_code=204)
def delete_version(
    project_id: str,
    version_ref: str,
    service: VersionService = Depends(get_version_service),
):
    try:
        service.delete_version(project_id, version_ref)
    except VersionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="项目不存在") from exc
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="版本不存在") from exc
    except VersionPinnedError as exc:
        raise HTTPException(status_code=409, detail="已标记的版本不能删除，请先取消标记") from exc


@router.post(
    "/{project_id}/versions/{version_ref:path}/restore",
    response_model=RestoreVersionResponse,
)
def restore_version(
    project_id: str,
    version_ref: str,
    service: VersionService = Depends(get_version_service),
):
    try:
        return service.restore(project_id, version_ref)
    except VersionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="项目不存在") from exc
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="版本不存在") from exc
    except VersionEntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="原始实体不存在") from exc
    except VersionRestoreMismatchError as exc:
        raise HTTPException(status_code=409, detail="版本与实体不匹配") from exc
