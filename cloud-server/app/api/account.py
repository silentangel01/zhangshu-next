"""Account management API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_session_id, get_current_user
from app.core.audit import audit_event
from app.db.session import get_db
from app.models.user import User
from app.schemas.account import (
    AvatarCompleteRequest,
    AvatarInitRequest,
    AvatarInitResponse,
    AvatarResponse,
    BindEmailCodeRequest,
    BindEmailRequest,
    BindPhoneCodeRequest,
    BindPhoneRequest,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ConfirmDeleteRequest,
    DeleteAccountResponse,
    DeleteRequestBody,
    DeletionRequestResponse,
    ProfileResponse,
    RevokeAllResponse,
    SessionListResponse,
    SessionResponse,
    UpdateProfileRequest,
)
from app.schemas.usage import UsageResponse
from app.services.account_service import AccountError, AccountService
from app.services.email_verification_service import (
    EmailVerificationError,
    EmailVerificationService,
)
from app.services.phone_verification_service import (
    PhoneVerificationError,
    PhoneVerificationService,
)
from app.services.rate_limit_service import RateLimitError, RateLimitService
from app.services.usage_service import UsageService
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/api/account", tags=["account"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ------------------------------------------------------------------
# Profile
# ------------------------------------------------------------------

@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AccountService(db)
    return svc.get_profile(current_user.id)


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    body: UpdateProfileRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AccountService(db)
    try:
        result = svc.update_profile(
            current_user.id,
            display_name=body.display_name,
            signature=body.signature,
        )
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    ActivityService(db).record(current_user.id, "profile_updated", request)
    return result


@router.post("/bind/email-code/send")
def send_bind_email_code(
    body: BindEmailCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return EmailVerificationService(db).send_code(body.email, "bind")
    except EmailVerificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/bind/phone-code/send")
def send_bind_phone_code(
    body: BindPhoneCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return PhoneVerificationService(db).send_code(body.phone_number, "bind")
    except PhoneVerificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/bind/email", response_model=ProfileResponse)
def bind_email(
    body: BindEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = AccountService(db).bind_email(
            current_user.id, body.email, body.verification_code
        )
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    ActivityService(db).record(current_user.id, "email_bound", request)
    return result


@router.post("/bind/phone", response_model=ProfileResponse)
def bind_phone(
    body: BindPhoneRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = AccountService(db).bind_phone(
            current_user.id, body.phone_number, body.verification_code
        )
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    ActivityService(db).record(current_user.id, "phone_bound", request)
    return result


# ------------------------------------------------------------------
# Avatar
# ------------------------------------------------------------------


@router.post("/avatar/init", response_model=AvatarInitResponse)
def init_avatar_upload(
    body: AvatarInitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AccountService(db)
    try:
        return svc.init_avatar_upload(
            current_user.id, body.filename, body.content_type, body.size_bytes
        )
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/avatar/complete", response_model=AvatarResponse)
def complete_avatar_upload(
    body: AvatarCompleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AccountService(db)
    try:
        result = svc.complete_avatar_upload(
            current_user.id, body.object_key, body.content_type
        )
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    ActivityService(db).record(current_user.id, "avatar_updated", request)
    return result


@router.delete("/avatar", response_model=AvatarResponse)
def delete_avatar(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AccountService(db)
    try:
        result = svc.delete_avatar(current_user.id)
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    ActivityService(db).record(current_user.id, "avatar_deleted", request)
    return result


# ------------------------------------------------------------------
# Password
# ------------------------------------------------------------------

@router.post("/password/change", response_model=ChangePasswordResponse)
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Rate limit password changes
    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_password_change(
            current_user.id, limit=3, window_seconds=600,
            client_ip=_client_ip(request),
        )
    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="密码修改过于频繁，请稍后再试。",
        )

    svc = AccountService(db)
    try:
        result = svc.change_password(
            current_user.id, body.old_password, body.new_password
        )
    except AccountError as exc:
        audit_event(
            "password_change_failed",
            request_id=_request_id(request),
            client_ip=_client_ip(request),
            user_id=current_user.id,
            result="failure",
            db=db,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "password_changed",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=current_user.id,
        db=db,
    )
    ActivityService(db).record(current_user.id, "password_changed", request)
    return result


# ------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------

@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_session_id: str | None = Depends(get_current_session_id),
):
    svc = AccountService(db)
    sessions = svc.list_sessions(current_user.id, current_session_id=current_session_id)
    return {
        "sessions": [SessionResponse(**s) for s in sessions],
        "total": len(sessions),
    }


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AccountService(db)
    try:
        svc.revoke_session(current_user.id, session_id)
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/sessions/revoke-all", response_model=RevokeAllResponse)
def revoke_all_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AccountService(db)
    try:
        result = svc.revoke_all_sessions(current_user.id)
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "sessions_revoked_all",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=current_user.id,
        db=db,
    )
    return result


# ------------------------------------------------------------------
# Usage
# ------------------------------------------------------------------

@router.get("/usage", response_model=UsageResponse)
def get_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = UsageService(db)
    return svc.get_usage(current_user.id)


# ------------------------------------------------------------------
# Export
# ------------------------------------------------------------------

@router.get("/export")
def export_account(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AccountService(db)
    try:
        data = svc.export_account_data(current_user.id)
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "account_exported",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=current_user.id,
        db=db,
    )
    return data


# ------------------------------------------------------------------
# Deletion (two-stage)
# ------------------------------------------------------------------

@router.post("/delete-request", response_model=DeletionRequestResponse)
def request_deletion(
    body: DeleteRequestBody,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Rate limit deletion attempts
    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_account_delete(
            current_user.id, limit=3, window_seconds=600,
            client_ip=_client_ip(request),
        )
    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="删除请求过于频繁，请稍后再试。",
        )

    svc = AccountService(db)
    try:
        result = svc.request_deletion(current_user.id, body.password)
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "account_delete_requested",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=current_user.id,
        db=db,
    )
    return result


@router.delete("", response_model=DeleteAccountResponse)
def delete_account(
    body: ConfirmDeleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AccountService(db)
    try:
        result = svc.confirm_deletion(
            current_user.id, body.request_id, body.confirmation_text
        )
    except AccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return result
