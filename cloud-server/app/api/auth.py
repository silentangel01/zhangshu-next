"""Authentication API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import audit_event
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import AuthError, AuthService
from app.services.rate_limit_service import RateLimitError, RateLimitService
from app.services.activity_service import ActivityService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_settings = get_settings()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _client_ip(request: Request) -> str:
    # Respect X-Forwarded-For from reverse proxy
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


@router.post("/register", response_model=TokenResponse)
def register(
    body: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)
    ua = _user_agent(request)

    # Database-level rate limit
    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_register(
            client_ip, body.email,
            limit=_settings.rate_limit_login_per_5m,
            window_seconds=300,
        )
    except RateLimitError:
        audit_event(
            "register_rate_limited",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code="rate_limited",
            db=db,
        )
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")

    service = AuthService(db)
    try:
        result = service.register(
            body.email, body.password, body.display_name,
            user_agent=ua, client_ip=client_ip,
        )
    except AuthError as exc:
        audit_event(
            "register_failed",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code=str(exc.status_code),
            extra={"email_domain": body.email.split("@")[-1] if "@" in body.email else ""},
            db=db,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "user_registered",
        request_id=_request_id(request),
        client_ip=client_ip,
        user_id=result.get("user_id", ""),
        extra={"email_domain": body.email.split("@")[-1] if "@" in body.email else ""},
        db=db,
    )
    ActivityService(db).record(result.get("user_id"), "user_registered", request)
    return result


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)
    ua = _user_agent(request)

    # Database-level rate limit
    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_login(
            client_ip, body.email,
            limit=_settings.rate_limit_login_per_5m,
            window_seconds=300,
        )
    except RateLimitError:
        audit_event(
            "login_rate_limited",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code="rate_limited",
            db=db,
        )
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")

    service = AuthService(db)
    try:
        result = service.login(
            body.email, body.password,
            user_agent=ua, client_ip=client_ip,
        )
    except AuthError as exc:
        audit_event(
            "login_failed",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code=str(exc.status_code),
            extra={"email_domain": body.email.split("@")[-1] if "@" in body.email else ""},
            db=db,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "login_success",
        request_id=_request_id(request),
        client_ip=client_ip,
        user_id=result.get("user_id", ""),
        db=db,
    )
    ActivityService(db).record(result.get("user_id"), "login_success", request)
    return result


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    body: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)
    ua = _user_agent(request)

    service = AuthService(db)
    try:
        result = service.refresh(
            body.refresh_token,
            user_agent=ua, client_ip=client_ip,
        )
    except AuthError as exc:
        audit_event(
            "token_refresh_failed",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code=str(exc.status_code),
            db=db,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "token_refreshed",
        request_id=_request_id(request),
        client_ip=client_ip,
        user_id=result.get("user_id", ""),
        db=db,
    )
    ActivityService(db).record(result.get("user_id"), "token_refreshed", request)
    return result


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "display_name": current_user.display_name,
    }
