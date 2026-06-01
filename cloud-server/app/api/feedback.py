"""Public feedback API — supports anonymous and authenticated submissions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_current_user
from app.core.audit import audit_event
from app.db.session import get_db
from app.models.user import User
from app.schemas.feedback import (
    ClientFeedbackListResponse,
    FeedbackCompleteRequest,
    FeedbackCompleteResponse,
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    FeedbackReplyResponse,
)
from app.services.feedback_service import FeedbackError, FeedbackService
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.get("", response_model=ClientFeedbackListResponse)
def list_user_feedback(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientFeedbackListResponse:
    """List the authenticated user's own feedback tickets."""
    svc = FeedbackService(db)
    return svc.list_user_feedback(user.id, limit=limit, offset=offset)


@router.post("", response_model=FeedbackCreateResponse, status_code=201)
def create_feedback(
    req: FeedbackCreateRequest,
    user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
) -> FeedbackCreateResponse:
    """Submit feedback. Authentication is optional.

    - Authenticated users: feedback is linked to their account.
    - Anonymous users: only contact_email (optional) is stored.
    """
    svc = FeedbackService(db)
    try:
        result = svc.create_feedback(
            req,
            user_id=user.id if user else None,
            client_ip=_client_ip(request),
        )
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "feedback_created",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=user.id if user else None,
        result="success",
        db=db,
    )
    ActivityService(db).record(
        user.id if user else None,
        "feedback_created",
        request,
        metadata={"category": req.category},
    )
    return result


@router.post("/{feedback_id}/complete", response_model=FeedbackCompleteResponse)
def complete_feedback(
    feedback_id: str,
    req: FeedbackCompleteRequest,
    db: Session = Depends(get_db),
    request: Request = None,
) -> FeedbackCompleteResponse:
    """Confirm attachment uploads and finalize the feedback ticket."""
    svc = FeedbackService(db)
    try:
        result = svc.complete_feedback(
            feedback_id,
            req,
            client_ip=_client_ip(request),
        )
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "feedback_completed",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        result="success",
        db=db,
    )
    return result


@router.get("/{feedback_id}/replies", response_model=list[FeedbackReplyResponse])
def list_feedback_replies(
    feedback_id: str,
    user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> list[FeedbackReplyResponse]:
    """View admin replies for a feedback ticket.

    - Anonymous tickets: anyone can view replies (UUID acts as secret).
    - Authenticated tickets: only the ticket owner can view replies.
    """
    svc = FeedbackService(db)
    # Ownership check for authenticated-user tickets
    ticket = svc._repo.get_ticket(feedback_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="反馈不存在。")
    if ticket.user_id and user and ticket.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看此反馈。")

    try:
        result = svc.list_replies_admin(feedback_id)
    except FeedbackError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return result.items
