"""Cloud auth, backup, and network diagnostics API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.cloud_api_client import CloudApiNotConfiguredError
from app.infrastructure.database import get_db
from app.schemas.cloud import (
    CloudAccountStatus,
    CloudBackupListResponse,
    CloudBackupRecordResponse,
    CloudDiagnosticRunRequest,
    CloudEnableRequest,
    CloudLoginRequest,
    CloudNetworkSettingsRequest,
    CloudNetworkSettingsResponse,
    CloudProjectStatus,
    CloudRegisterRequest,
)
from app.services.cloud_auth_service import CloudAuthError, CloudAuthService
from app.services.cloud_backup_service import CloudBackupError, CloudBackupService
from app.services.cloud_network_service import CloudNetworkService


# ── Dependencies ──────────────────────────────────────────────────


def get_auth_service(db: Session = Depends(get_db)) -> CloudAuthService:
    return CloudAuthService(db)


def get_cloud_backup_service(
    db: Session = Depends(get_db),
) -> CloudBackupService:
    return CloudBackupService(db)


def get_network_service(
    db: Session = Depends(get_db),
) -> CloudNetworkService:
    return CloudNetworkService(db)


def _build_error_detail(exc: Exception) -> dict[str, str] | str:
    """Build an HTTP error detail from a service error.

    If the error has ``error_kind`` or ``suggestion``, returns a structured
    dict so the frontend can show targeted guidance. Otherwise returns the
    plain error message string.
    """
    kind = getattr(exc, "error_kind", "")
    suggestion = getattr(exc, "suggestion", "")
    if kind or suggestion:
        result: dict[str, str] = {"message": str(exc)}
        if kind:
            result["error_kind"] = kind
        if suggestion:
            result["suggestion"] = suggestion
        return result
    return str(exc)


# ── Auth router ───────────────────────────────────────────────────

router = APIRouter(tags=["cloud"])


@router.get("/api/cloud/account/status")
def get_account_status(
    service: CloudAuthService = Depends(get_auth_service),
):
    return service.get_account_status()


@router.post("/api/cloud/auth/login")
def cloud_login(
    body: CloudLoginRequest,
    service: CloudAuthService = Depends(get_auth_service),
):
    try:
        return service.login(body.email, body.password)
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=401, detail=_build_error_detail(exc)
        ) from exc


@router.post("/api/cloud/auth/register")
def cloud_register(
    body: CloudRegisterRequest,
    service: CloudAuthService = Depends(get_auth_service),
):
    try:
        return service.register(body.email, body.password, body.display_name)
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=400, detail=_build_error_detail(exc)
        ) from exc


@router.post("/api/cloud/auth/logout")
def cloud_logout(
    service: CloudAuthService = Depends(get_auth_service),
):
    service.logout()
    return {"ok": True}


# ── Network diagnostics router ───────────────────────────────────────


@router.get("/api/cloud/network/settings")
def get_network_settings(
    service: CloudNetworkService = Depends(get_network_service),
):
    return service.get_settings()


@router.put("/api/cloud/network/settings")
def set_network_settings(
    body: CloudNetworkSettingsRequest,
    service: CloudNetworkService = Depends(get_network_service),
):
    try:
        return service.set_mode(body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/cloud/network/diagnose")
def run_network_diagnostics(
    body: CloudDiagnosticRunRequest | None = None,
    service: CloudNetworkService = Depends(get_network_service),
):
    report = service.run_diagnostics()
    return report


# ── Project cloud router ─────────────────────────────────────────

projects_cloud_router = APIRouter(
    prefix="/api/projects", tags=["cloud"]
)


@projects_cloud_router.post("/{project_id}/cloud/enable")
def enable_cloud(
    project_id: str,
    body: CloudEnableRequest | None = None,
    service: CloudBackupService = Depends(get_cloud_backup_service),
):
    cloud_project_id = body.cloud_project_id if body else None
    try:
        link = service.enable_cloud(project_id, cloud_project_id)
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudBackupError as exc:
        detail = _build_error_detail(exc)
        raise HTTPException(status_code=400, detail=detail) from exc

    return {
        "cloud_enabled": link.cloud_enabled,
        "cloud_project_id": link.cloud_project_id,
        "provider": link.provider,
        "last_backup_at": link.last_backup_at,
        "last_restore_at": link.last_restore_at,
        "status": link.status,
        "last_error": link.last_error,
    }


@projects_cloud_router.get("/{project_id}/cloud/status")
def get_cloud_status(
    project_id: str,
    service: CloudBackupService = Depends(get_cloud_backup_service),
):
    return service.get_status(project_id)


@projects_cloud_router.post("/{project_id}/cloud/backups")
def trigger_cloud_backup(
    project_id: str,
    service: CloudBackupService = Depends(get_cloud_backup_service),
):
    try:
        record = service.trigger_backup(project_id)
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudBackupError as exc:
        raise HTTPException(
            status_code=400, detail=_build_error_detail(exc)
        ) from exc

    return CloudBackupRecordResponse.model_validate(record)


@projects_cloud_router.get("/{project_id}/cloud/backups")
def list_cloud_backups(
    project_id: str,
    service: CloudBackupService = Depends(get_cloud_backup_service),
):
    records = service.list_backups(project_id)
    items = [CloudBackupRecordResponse.model_validate(r) for r in records]
    return CloudBackupListResponse(items=items, total=len(items))


@projects_cloud_router.post(
    "/{project_id}/cloud/backups/{record_id}/restore"
)
def restore_cloud_backup(
    project_id: str,
    record_id: str,
    service: CloudBackupService = Depends(get_cloud_backup_service),
):
    try:
        return service.restore_backup(project_id, record_id)
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudBackupError as exc:
        raise HTTPException(
            status_code=400, detail=_build_error_detail(exc)
        ) from exc
