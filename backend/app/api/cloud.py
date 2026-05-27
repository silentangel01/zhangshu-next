"""Cloud auth, backup, and network diagnostics API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.infrastructure.cloud_api_client import CloudApiNotConfiguredError
from app.infrastructure.database import get_db
from app.schemas.cloud import (
    CloudAccountStatus,
    CloudBackupListResponse,
    CloudBackupRecordResponse,
    CloudChangePasswordRequest,
    CloudConfirmDeleteRequest,
    CloudDeleteAccountRequest,
    CloudDiagnosticRunRequest,
    CloudEnableRequest,
    CloudLoginRequest,
    CloudNetworkSettingsRequest,
    CloudNetworkSettingsResponse,
    CloudProjectStatus,
    CloudRegisterRequest,
    CloudUpdateProfileRequest,
)
from app.services.cloud_announcement_service import CloudAnnouncementService
from app.services.cloud_auth_service import CloudAuthError, CloudAuthService
from app.services.cloud_backup_service import CloudBackupError, CloudBackupService
from app.services.cloud_feedback_service import CloudFeedbackError, CloudFeedbackService
from app.services.cloud_network_service import CloudNetworkService
from app.services.cloud_profile_service import CloudProfileError, CloudProfileService


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


def get_announcement_service(
    db: Session = Depends(get_db),
) -> CloudAnnouncementService:
    return CloudAnnouncementService(CloudAuthService(db))


def get_feedback_service(
    db: Session = Depends(get_db),
) -> CloudFeedbackService:
    return CloudFeedbackService(CloudAuthService(db))


def get_profile_service(
    db: Session = Depends(get_db),
) -> CloudProfileService:
    return CloudProfileService(CloudAuthService(db))


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


# ── Account proxy router ────────────────────────────────────────────


@router.get("/api/cloud/account/profile")
def cloud_get_profile(
    service: CloudProfileService = Depends(get_profile_service),
):
    try:
        return service.get_profile()
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (CloudAuthError, CloudProfileError) as exc:
        raise HTTPException(
            status_code=401, detail=_build_error_detail(exc)
        ) from exc


@router.patch("/api/cloud/account/profile")
def cloud_update_profile(
    body: CloudUpdateProfileRequest,
    service: CloudProfileService = Depends(get_profile_service),
):
    try:
        return service.update_profile(
            display_name=body.display_name,
            signature=body.signature,
        )
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (CloudAuthError, CloudProfileError) as exc:
        raise HTTPException(
            status_code=400, detail=_build_error_detail(exc)
        ) from exc


@router.post("/api/cloud/account/password/change")
def cloud_change_password(
    body: CloudChangePasswordRequest,
    service: CloudProfileService = Depends(get_profile_service),
):
    try:
        return service.change_password(body.old_password, body.new_password)
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (CloudAuthError, CloudProfileError) as exc:
        raise HTTPException(
            status_code=400, detail=_build_error_detail(exc)
        ) from exc


@router.post("/api/cloud/account/avatar")
async def cloud_upload_avatar(
    file: UploadFile = File(...),
    service: CloudProfileService = Depends(get_profile_service),
):
    """Upload a new avatar image via multipart form.

    Validates type (png/jpeg/webp) and size (max 2 MB).
    Coordinates the three-step upload with the cloud server.
    """
    try:
        return await service.upload_avatar(file)
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=401, detail=_build_error_detail(exc)
        ) from exc


@router.delete("/api/cloud/account/avatar")
def cloud_delete_avatar(
    service: CloudProfileService = Depends(get_profile_service),
):
    """Delete the user's avatar."""
    try:
        result = service.delete_avatar()
        return result or {"ok": True}
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (CloudAuthError, CloudProfileError) as exc:
        raise HTTPException(
            status_code=400, detail=_build_error_detail(exc)
        ) from exc


@router.post("/api/cloud/account/sessions/revoke-all")
def cloud_revoke_all_sessions(
    service: CloudAuthService = Depends(get_auth_service),
):
    try:
        result = service.revoke_all_sessions()
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=400, detail=_build_error_detail(exc)
        ) from exc

    # After revoking all sessions, clear local tokens
    service.logout()
    return result


@router.get("/api/cloud/account/usage")
def cloud_get_usage(
    service: CloudAuthService = Depends(get_auth_service),
):
    try:
        return service.get_usage()
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=401, detail=_build_error_detail(exc)
        ) from exc


@router.get("/api/cloud/account/export")
def cloud_export_data(
    service: CloudAuthService = Depends(get_auth_service),
):
    try:
        return service.export_account_data()
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=401, detail=_build_error_detail(exc)
        ) from exc


@router.post("/api/cloud/account/delete-request")
def cloud_request_deletion(
    body: CloudDeleteAccountRequest,
    service: CloudAuthService = Depends(get_auth_service),
):
    try:
        return service.request_account_deletion(body.password)
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=400, detail=_build_error_detail(exc)
        ) from exc


@router.delete("/api/cloud/account")
def cloud_delete_account(
    body: CloudConfirmDeleteRequest,
    service: CloudAuthService = Depends(get_auth_service),
):
    try:
        result = service.confirm_account_deletion(
            body.request_id, body.confirmation_text
        )
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=400, detail=_build_error_detail(exc)
        ) from exc

    # After account deletion, clear local tokens
    service.logout()
    return result


# ── Announcement proxy routes ───────────────────────────────────────


@router.get("/api/cloud/announcements")
def list_cloud_announcements(
    platform: str | None = None,
    app_version: str | None = None,
    service: CloudAnnouncementService = Depends(get_announcement_service),
):
    """Fetch active announcements from the cloud server.

    Silently returns empty list when cloud is unavailable.
    """
    return service.list_announcements(platform=platform, app_version=app_version)


# ── Feedback proxy routes ──────────────────────────────────────────


@router.post("/api/cloud/feedback")
async def submit_cloud_feedback(
    category: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    contact_email: str | None = Form(default=None),
    include_diagnostics: bool = Form(default=False),
    attachments: list[UploadFile] | None = File(default=None),
    service: CloudFeedbackService = Depends(get_feedback_service),
):
    """Submit feedback with optional file attachments via multipart form.

    The sidecar validates files, computes checksums, coordinates upload
    to OSS via presigned URLs, and confirms completion.
    """
    try:
        return await service.submit_feedback(
            category=category,
            title=title,
            description=description,
            contact_email=contact_email,
            include_diagnostics=include_diagnostics,
            files=attachments if attachments else None,
        )
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudFeedbackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/cloud/feedback/{feedback_id}/replies")
def list_cloud_feedback_replies(
    feedback_id: str,
    service: CloudFeedbackService = Depends(get_feedback_service),
):
    """Fetch admin replies for a feedback ticket from the cloud server."""
    try:
        return service.list_ticket_replies(feedback_id)
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=401, detail=_build_error_detail(exc)
        ) from exc
    except CloudFeedbackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/cloud/feedback")
def list_cloud_feedback_history(
    limit: int = 50,
    offset: int = 0,
    service: CloudFeedbackService = Depends(get_feedback_service),
):
    """List the authenticated user's feedback history from the cloud server."""
    try:
        return service.list_user_feedback(limit=limit, offset=offset)
    except CloudApiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CloudAuthError as exc:
        raise HTTPException(
            status_code=401, detail=_build_error_detail(exc)
        ) from exc
    except CloudFeedbackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
