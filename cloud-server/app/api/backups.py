"""Backup management API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import audit_event
from app.db.session import get_db
from app.models.user import User
from app.schemas.backup import (
    BackupListResponse,
    BackupResponse,
    CompleteBackupRequest,
    CompleteBackupResponse,
    DownloadUrlResponse,
    InitBackupRequest,
    InitBackupResponse,
)
from app.services.backup_service import BackupError, BackupService
from app.services.project_service import ProjectError

router = APIRouter(prefix="/api/projects", tags=["backups"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post(
    "/{project_id}/backups/init",
    response_model=InitBackupResponse,
)
def init_backup(
    project_id: str,
    body: InitBackupRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BackupService(db)
    try:
        result = service.init_upload(
            project_id, current_user.id, body.filename, body.size_bytes
        )
    except (BackupError, ProjectError) as exc:
        audit_event(
            "backup_init_failed",
            request_id=_request_id(request),
            client_ip=_client_ip(request),
            user_id=current_user.id,
            project_id=project_id,
            result="failure",
            reason_code=str(exc.status_code),
            extra={"size_bytes": body.size_bytes},
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "backup_init",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=current_user.id,
        project_id=project_id,
        extra={"file_name": body.filename, "size_bytes": body.size_bytes},
    )
    return result


@router.post(
    "/{project_id}/backups/complete",
    response_model=CompleteBackupResponse,
)
def complete_backup(
    project_id: str,
    body: CompleteBackupRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BackupService(db)
    try:
        result = service.complete_upload(
            project_id,
            current_user.id,
            body.upload_id,
            body.checksum_sha256,
        )
    except (BackupError, ProjectError) as exc:
        audit_event(
            "backup_complete_failed",
            request_id=_request_id(request),
            client_ip=_client_ip(request),
            user_id=current_user.id,
            project_id=project_id,
            result="failure",
            reason_code=str(exc.status_code),
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "backup_complete",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=current_user.id,
        project_id=project_id,
        backup_id=result.get("id", ""),
    )
    return result


@router.get(
    "/{project_id}/backups",
    response_model=BackupListResponse,
)
def list_backups(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BackupService(db)
    try:
        items, total = service.list_backups(project_id, current_user.id)
    except (BackupError, ProjectError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    backup_items = [
        BackupResponse(
            id=b.id,
            filename=b.filename,
            size_bytes=b.size_bytes,
            checksum_sha256=b.checksum_sha256,
            status=b.status,
            created_at=b.created_at,
            uploaded_at=b.uploaded_at,
        )
        for b in items
    ]
    return BackupListResponse(items=backup_items, total=total)


@router.get(
    "/{project_id}/backups/{backup_id}/download-url",
    response_model=DownloadUrlResponse,
)
def get_download_url(
    project_id: str,
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BackupService(db)
    try:
        url = service.get_download_url(
            project_id, current_user.id, backup_id
        )
    except (BackupError, ProjectError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return DownloadUrlResponse(download_url=url)


@router.delete(
    "/{project_id}/backups/{backup_id}",
    status_code=204,
)
def delete_backup(
    project_id: str,
    backup_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BackupService(db)
    try:
        service.delete_backup(project_id, current_user.id, backup_id)
    except (BackupError, ProjectError) as exc:
        audit_event(
            "backup_delete_failed",
            request_id=_request_id(request),
            client_ip=_client_ip(request),
            user_id=current_user.id,
            project_id=project_id,
            backup_id=backup_id,
            result="failure",
            reason_code=str(exc.status_code),
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "backup_deleted",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=current_user.id,
        project_id=project_id,
        backup_id=backup_id,
    )
    return Response(status_code=204)
