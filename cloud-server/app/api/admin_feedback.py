"""Admin feedback management API — permission-graded endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permission
from app.core.admin_permissions import (
    FEEDBACK_ATTACHMENT_DOWNLOAD,
    FEEDBACK_MANAGE,
    FEEDBACK_REPLY,
    FEEDBACK_VIEW,
)
from app.core.audit import audit_event
from app.db.session import get_db
from app.models.user import User
from app.schemas.feedback import (
    AdminDownloadUrlResponse,
    AdminFeedbackListResponse,
    AdminFeedbackReplyCreateRequest,
    AdminFeedbackReplyListResponse,
    AdminFeedbackResponse,
    AdminFeedbackUpdateRequest,
    FeedbackReplyResponse,
)
from app.services.feedback_service import FeedbackError, FeedbackService

router = APIRouter(prefix="/api/admin/feedback", tags=["admin-feedback"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.get("", response_model=AdminFeedbackListResponse)
def list_feedback(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin_permission(FEEDBACK_VIEW)),
    db: Session = Depends(get_db),
) -> AdminFeedbackListResponse:
    svc = FeedbackService(db)
    return svc.list_admin(status=status, category=category, limit=limit, offset=offset)


@router.get("/{feedback_id}", response_model=AdminFeedbackResponse)
def get_feedback(
    feedback_id: str,
    admin: User = Depends(require_admin_permission(FEEDBACK_VIEW)),
    db: Session = Depends(get_db),
    request: Request = None,
) -> AdminFeedbackResponse:
    svc = FeedbackService(db)
    try:
        result = svc.get_admin(feedback_id)
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "admin_feedback_viewed",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={"feedback_id": feedback_id},
        db=db,
    )
    return result


@router.patch("/{feedback_id}", response_model=AdminFeedbackResponse)
def update_feedback(
    feedback_id: str,
    req: AdminFeedbackUpdateRequest,
    admin: User = Depends(require_admin_permission(FEEDBACK_MANAGE)),
    db: Session = Depends(get_db),
    request: Request = None,
) -> AdminFeedbackResponse:
    svc = FeedbackService(db)
    try:
        result = svc.update_admin(feedback_id, req)
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "admin_feedback_updated",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={"feedback_id": feedback_id, "permission": FEEDBACK_MANAGE},
        db=db,
    )
    return result


@router.get(
    "/{feedback_id}/attachments/{attachment_id}/download-url",
    response_model=AdminDownloadUrlResponse,
)
def get_attachment_download_url(
    feedback_id: str,
    attachment_id: str,
    reason: str = Query(
        ..., min_length=1, max_length=500,
        description="Reason for downloading this attachment.",
    ),
    admin: User = Depends(require_admin_permission(FEEDBACK_ATTACHMENT_DOWNLOAD)),
    db: Session = Depends(get_db),
    request: Request = None,
) -> AdminDownloadUrlResponse:
    """Generate a short-lived presigned download URL for a feedback attachment.

    Requires ``feedback:attachment_download`` permission and a mandatory reason.
    """
    svc = FeedbackService(db)
    try:
        result = svc.get_download_url(feedback_id, attachment_id)
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "admin_feedback_download_url",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={
            "feedback_id": feedback_id,
            "attachment_id": attachment_id,
            "action_reason": reason,
            "risk_level": "medium",
            "permission": FEEDBACK_ATTACHMENT_DOWNLOAD,
        },
        db=db,
    )
    return result


@router.get("/{feedback_id}/replies", response_model=AdminFeedbackReplyListResponse)
def list_feedback_replies(
    feedback_id: str,
    _admin: User = Depends(require_admin_permission(FEEDBACK_VIEW)),
    db: Session = Depends(get_db),
) -> AdminFeedbackReplyListResponse:
    svc = FeedbackService(db)
    try:
        return svc.list_replies_admin(feedback_id)
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post(
    "/{feedback_id}/replies",
    response_model=FeedbackReplyResponse,
    status_code=201,
)
def create_feedback_reply(
    feedback_id: str,
    req: AdminFeedbackReplyCreateRequest,
    admin: User = Depends(require_admin_permission(FEEDBACK_REPLY)),
    db: Session = Depends(get_db),
    request: Request = None,
) -> FeedbackReplyResponse:
    svc = FeedbackService(db)
    try:
        result = svc.create_reply_admin(feedback_id, req, admin_user_id=admin.id)
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "admin_feedback_reply_created",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={"feedback_id": feedback_id, "permission": FEEDBACK_REPLY},
        db=db,
    )
    return result


@router.delete("/{feedback_id}/replies/{reply_id}", status_code=204)
def delete_feedback_reply(
    feedback_id: str,
    reply_id: str,
    admin: User = Depends(require_admin_permission(FEEDBACK_MANAGE)),
    db: Session = Depends(get_db),
    request: Request = None,
) -> None:
    svc = FeedbackService(db)
    try:
        svc.delete_reply_admin(feedback_id, reply_id)
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "admin_feedback_reply_deleted",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={"feedback_id": feedback_id, "permission": FEEDBACK_MANAGE},
        db=db,
    )


@router.delete("/{feedback_id}", status_code=204)
def delete_feedback(
    feedback_id: str,
    reason: str = Query(
        ..., min_length=1, max_length=500,
        description="Reason for deleting this feedback.",
    ),
    admin: User = Depends(require_admin_permission(FEEDBACK_MANAGE)),
    db: Session = Depends(get_db),
    request: Request = None,
) -> None:
    """Soft-delete a feedback ticket and its attachments. Requires reason."""
    svc = FeedbackService(db)
    try:
        svc.delete_admin(feedback_id)
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "admin_feedback_deleted",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={
            "feedback_id": feedback_id,
            "action_reason": reason,
            "risk_level": "high",
            "permission": FEEDBACK_MANAGE,
        },
        db=db,
    )
