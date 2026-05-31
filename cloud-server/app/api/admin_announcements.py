"""Admin announcement management API — permission-graded endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permission
from app.core.admin_permissions import (
    ANNOUNCEMENTS_DELETE,
    ANNOUNCEMENTS_PUBLISH,
    ANNOUNCEMENTS_VIEW,
    ANNOUNCEMENTS_WRITE,
)
from app.core.audit import audit_event
from app.db.session import get_db
from app.models.user import User
from app.schemas.announcement import (
    AdminAnnouncementListResponse,
    AdminAnnouncementResponse,
    AnnouncementCreateRequest,
    AnnouncementUpdateRequest,
)
from app.services.announcement_service import AnnouncementError, AnnouncementService

router = APIRouter(prefix="/api/admin/announcements", tags=["admin-announcements"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("", response_model=AdminAnnouncementResponse, status_code=201)
def create_announcement(
    req: AnnouncementCreateRequest,
    admin: User = Depends(require_admin_permission(ANNOUNCEMENTS_WRITE)),
    db: Session = Depends(get_db),
    request: Request = None,
) -> AdminAnnouncementResponse:
    svc = AnnouncementService(db)
    try:
        result = svc.create(req, admin_user_id=admin.id)
    except AnnouncementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "admin_announcement_created",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={"announcement_id": result.id, "permission": ANNOUNCEMENTS_WRITE},
        db=db,
    )
    return result


@router.get("", response_model=AdminAnnouncementListResponse)
def list_announcements(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin_permission(ANNOUNCEMENTS_VIEW)),
    db: Session = Depends(get_db),
) -> AdminAnnouncementListResponse:
    svc = AnnouncementService(db)
    return svc.list_admin(status=status, limit=limit, offset=offset)


@router.get("/{announcement_id}", response_model=AdminAnnouncementResponse)
def get_announcement(
    announcement_id: str,
    _admin: User = Depends(require_admin_permission(ANNOUNCEMENTS_VIEW)),
    db: Session = Depends(get_db),
) -> AdminAnnouncementResponse:
    svc = AnnouncementService(db)
    try:
        return svc.get_admin(announcement_id)
    except AnnouncementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.patch("/{announcement_id}", response_model=AdminAnnouncementResponse)
def update_announcement(
    announcement_id: str,
    req: AnnouncementUpdateRequest,
    _admin: User = Depends(require_admin_permission(ANNOUNCEMENTS_WRITE)),
    db: Session = Depends(get_db),
) -> AdminAnnouncementResponse:
    svc = AnnouncementService(db)
    try:
        return svc.update(announcement_id, req)
    except AnnouncementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{announcement_id}/publish", response_model=AdminAnnouncementResponse)
def publish_announcement(
    announcement_id: str,
    admin: User = Depends(require_admin_permission(ANNOUNCEMENTS_PUBLISH)),
    db: Session = Depends(get_db),
    request: Request = None,
) -> AdminAnnouncementResponse:
    svc = AnnouncementService(db)
    try:
        result = svc.publish(announcement_id)
    except AnnouncementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "admin_announcement_published",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={
            "announcement_id": announcement_id,
            "permission": ANNOUNCEMENTS_PUBLISH,
        },
        db=db,
    )
    return result


@router.post("/{announcement_id}/archive", response_model=AdminAnnouncementResponse)
def archive_announcement(
    announcement_id: str,
    admin: User = Depends(require_admin_permission(ANNOUNCEMENTS_WRITE)),
    db: Session = Depends(get_db),
    request: Request = None,
) -> AdminAnnouncementResponse:
    svc = AnnouncementService(db)
    try:
        result = svc.archive(announcement_id)
    except AnnouncementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "admin_announcement_archived",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={"announcement_id": announcement_id},
        db=db,
    )
    return result


@router.delete("/{announcement_id}", status_code=204)
def delete_announcement(
    announcement_id: str,
    admin: User = Depends(require_admin_permission(ANNOUNCEMENTS_DELETE)),
    db: Session = Depends(get_db),
    request: Request = None,
) -> None:
    svc = AnnouncementService(db)
    try:
        svc.delete(announcement_id)
    except AnnouncementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "admin_announcement_deleted",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={
            "announcement_id": announcement_id,
            "risk_level": "medium",
            "permission": ANNOUNCEMENTS_DELETE,
        },
        db=db,
    )
