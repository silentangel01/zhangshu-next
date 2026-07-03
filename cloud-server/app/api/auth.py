"""Authentication API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import audit_event
from app.core.config import get_settings
from app.core.security import normalize_email
from app.core.security import normalize_phone_number
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.repositories.auth_identity_repo import AuthIdentityRepository
from app.schemas.auth import (
    EmailCheckRequest,
    EmailCheckResponse,
    EmailCodeLoginRequest,
    LoginRequest,
    MeResponse,
    OAuthPollResponse,
    OAuthStartResponse,
    PhoneCheckRequest,
    PhoneCheckResponse,
    PhoneCodeLoginRequest,
    PhoneRegisterRequest,
    RefreshRequest,
    RegisterRequest,
    SendEmailCodeRequest,
    SendPhoneCodeRequest,
    SendEmailCodeResponse,
    TokenResponse,
)
from app.services.auth_service import AuthError, AuthService
from app.services.email_verification_service import (
    EmailVerificationError,
    EmailVerificationService,
)
from app.services.phone_verification_service import (
    PhoneVerificationError,
    PhoneVerificationService,
)
from app.services.oauth_auth_service import OAuthAuthError, OAuthAuthService
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


def _email_domain(email: str) -> str:
    return email.split("@")[-1] if "@" in email else ""


@router.post("/phone/check", response_model=PhoneCheckResponse)
def check_phone(
    body: PhoneCheckRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)
    try:
        normalized = normalize_phone_number(body.phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_phone_code_verify(
            client_ip,
            normalized,
            "check",
            limit=_settings.rate_limit_email_check_per_5m,
            window_seconds=300,
        )
    except RateLimitError:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")

    available = (
        AuthIdentityRepository(db).get_by_provider_identifier("phone", normalized)
        is None
    )
    return {"phone_number": normalized, "available": available}


@router.post("/email/check", response_model=EmailCheckResponse)
def check_email(
    body: EmailCheckRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)
    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_email_check(
            client_ip,
            body.email,
            limit=_settings.rate_limit_email_check_per_5m,
            window_seconds=300,
        )
    except RateLimitError:
        audit_event(
            "email_check_rate_limited",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code="rate_limited",
            db=db,
        )
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")

    normalized = normalize_email(body.email)
    identity_repo = AuthIdentityRepository(db)
    available = (
        UserRepository(db).get_by_email(normalized) is None
        and identity_repo.get_by_provider_identifier("email", normalized) is None
    )
    audit_event(
        "email_checked",
        request_id=_request_id(request),
        client_ip=client_ip,
        extra={"email_domain": _email_domain(normalized), "available": available},
        db=db,
    )
    return {"email": normalized, "available": available}


@router.post("/email-code/send", response_model=SendEmailCodeResponse)
def send_email_code(
    body: SendEmailCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)
    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_email_code_send(
            client_ip,
            body.email,
            body.purpose,
            limit=_settings.rate_limit_email_code_send_per_5m,
            window_seconds=300,
        )
    except RateLimitError:
        audit_event(
            "email_code_send_rate_limited",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code="rate_limited",
            extra={"purpose": body.purpose},
            db=db,
        )
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")

    try:
        result = EmailVerificationService(db).send_code(body.email, body.purpose)
    except EmailVerificationError as exc:
        audit_event(
            "email_code_send_failed",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code=exc.reason_code,
            extra={"email_domain": _email_domain(body.email), "purpose": body.purpose},
            db=db,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "email_code_sent",
        request_id=_request_id(request),
        client_ip=client_ip,
        extra={"email_domain": _email_domain(body.email), "purpose": body.purpose},
        db=db,
    )
    return result


@router.post("/phone-code/send", response_model=SendEmailCodeResponse)
def send_phone_code(
    body: SendPhoneCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)
    try:
        normalized = normalize_phone_number(body.phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_phone_code_send(
            client_ip,
            normalized,
            body.purpose,
            limit=_settings.rate_limit_email_code_send_per_5m,
            window_seconds=300,
        )
    except RateLimitError:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")

    try:
        result = PhoneVerificationService(db).send_code(normalized, body.purpose)
    except PhoneVerificationError as exc:
        audit_event(
            "phone_code_send_failed",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code=exc.reason_code,
            extra={"purpose": body.purpose},
            db=db,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "phone_code_sent",
        request_id=_request_id(request),
        client_ip=client_ip,
        extra={"purpose": body.purpose},
        db=db,
    )
    return result


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
        rl_svc.check_email_code_verify(
            client_ip,
            body.email,
            "register",
            limit=_settings.rate_limit_email_code_verify_per_5m,
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
            body.email, body.password, body.display_name, body.verification_code,
            user_agent=ua, client_ip=client_ip,
        )
    except AuthError as exc:
        audit_event(
            "register_failed",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code=str(exc.status_code),
            extra={"email_domain": _email_domain(body.email)},
            db=db,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "user_registered",
        request_id=_request_id(request),
        client_ip=client_ip,
        user_id=result.get("user_id", ""),
        extra={"email_domain": _email_domain(body.email)},
        db=db,
    )
    ActivityService(db).record(result.get("user_id"), "user_registered", request)
    return result


@router.post("/register/phone", response_model=TokenResponse)
def register_with_phone(
    body: PhoneRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)
    ua = _user_agent(request)
    try:
        normalized = normalize_phone_number(body.phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_register(
            client_ip, normalized,
            limit=_settings.rate_limit_login_per_5m,
            window_seconds=300,
        )
        rl_svc.check_phone_code_verify(
            client_ip,
            normalized,
            "register",
            limit=_settings.rate_limit_email_code_verify_per_5m,
            window_seconds=300,
        )
    except RateLimitError:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")

    try:
        result = AuthService(db).register_with_phone(
            normalized,
            body.verification_code,
            body.display_name,
            user_agent=ua,
            client_ip=client_ip,
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "user_registered_phone",
        request_id=_request_id(request),
        client_ip=client_ip,
        user_id=result.get("user_id", ""),
        db=db,
    )
    ActivityService(db).record(result.get("user_id"), "user_registered_phone", request)
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
            extra={"email_domain": _email_domain(body.email)},
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


@router.post("/login/email-code", response_model=TokenResponse)
def login_with_email_code(
    body: EmailCodeLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)
    ua = _user_agent(request)

    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_login(
            client_ip,
            body.email,
            limit=_settings.rate_limit_login_per_5m,
            window_seconds=300,
        )
        rl_svc.check_email_code_verify(
            client_ip,
            body.email,
            "login",
            limit=_settings.rate_limit_email_code_verify_per_5m,
            window_seconds=300,
        )
    except RateLimitError:
        audit_event(
            "email_code_login_rate_limited",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code="rate_limited",
            db=db,
        )
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")

    service = AuthService(db)
    try:
        result = service.login_with_email_code(
            body.email,
            body.verification_code,
            user_agent=ua,
            client_ip=client_ip,
        )
    except AuthError as exc:
        audit_event(
            "email_code_verify_failed",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code=str(exc.status_code),
            extra={"email_domain": _email_domain(body.email), "purpose": "login"},
            db=db,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "email_code_login_success",
        request_id=_request_id(request),
        client_ip=client_ip,
        user_id=result.get("user_id", ""),
        db=db,
    )
    ActivityService(db).record(
        result.get("user_id"), "email_code_login_success", request
    )
    return result


@router.post("/login/phone-code", response_model=TokenResponse)
def login_with_phone_code(
    body: PhoneCodeLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)
    ua = _user_agent(request)
    try:
        normalized = normalize_phone_number(body.phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_phone_code_verify(
            client_ip,
            normalized,
            "login",
            limit=_settings.rate_limit_email_code_verify_per_5m,
            window_seconds=300,
        )
    except RateLimitError:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")

    try:
        result = AuthService(db).login_with_phone_code(
            normalized,
            body.verification_code,
            user_agent=ua,
            client_ip=client_ip,
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    audit_event(
        "phone_code_login_success",
        request_id=_request_id(request),
        client_ip=client_ip,
        user_id=result.get("user_id", ""),
        db=db,
    )
    ActivityService(db).record(result.get("user_id"), "phone_code_login_success", request)
    return result


@router.post("/oauth/{provider}/start", response_model=OAuthStartResponse)
def start_oauth_login(
    provider: str,
    db: Session = Depends(get_db),
):
    try:
        return OAuthAuthService(db).start_login(provider)
    except OAuthAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/oauth/{provider}/callback", response_class=HTMLResponse)
def complete_oauth_login(
    provider: str,
    request: Request,
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code or not state:
        raise HTTPException(status_code=400, detail="第三方登录回调参数不完整。")
    try:
        return HTMLResponse(
            OAuthAuthService(db).complete_callback(
                provider,
                state=state,
                code=code,
                user_agent=_user_agent(request),
                client_ip=_client_ip(request),
            )
        )
    except OAuthAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/oauth/session/{session_id}", response_model=OAuthPollResponse)
def poll_oauth_login(
    session_id: str,
    poll_token: str,
    db: Session = Depends(get_db),
):
    try:
        return OAuthAuthService(db).poll_login(session_id, poll_token)
    except OAuthAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


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
