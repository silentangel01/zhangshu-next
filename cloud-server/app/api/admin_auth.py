"""Admin authentication API — HttpOnly Cookie based session management.

Admin sessions use short-lived access tokens (30 min) stored in HttpOnly
cookies, plus refresh tokens (8h) for session extension. This is more
secure than localStorage for admin panels (XSS resistant).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_from_admin_cookie, require_admin_user
from app.core.audit import audit_event
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_auth import AdminLoginRequest, AdminMeResponse
from app.services.activity_service import ActivityService
from app.services.auth_service import AuthError, AuthService
from app.services.rate_limit_service import RateLimitError, RateLimitService
from app.services.token_service import (
    TokenError,
    create_admin_access_token,
    create_admin_refresh_token,
    decode_token,
    hash_jti,
)
from app.repositories.refresh_token_repo import RefreshTokenRepository
from app.models.refresh_token import RefreshToken
from app.models.user import utc_now
from uuid import uuid4

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])
_settings = get_settings()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _set_admin_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set HttpOnly Secure cookies for admin session."""
    s = _settings
    response.set_cookie(
        key=s.admin_cookie_name,
        value=access_token,
        httponly=True,
        secure=s.admin_cookie_secure,
        samesite=s.admin_cookie_samesite,
        path=s.admin_cookie_path,
        max_age=s.admin_access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key=s.admin_refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=s.admin_cookie_secure,
        samesite=s.admin_cookie_samesite,
        path=s.admin_cookie_path,
        max_age=s.admin_refresh_token_expire_hours * 3600,
    )


def _clear_admin_cookies(response: Response) -> None:
    """Remove admin session cookies."""
    s = _settings
    response.delete_cookie(key=s.admin_cookie_name, path=s.admin_cookie_path)
    response.delete_cookie(key=s.admin_refresh_cookie_name, path=s.admin_cookie_path)


@router.post("/login", response_model=AdminMeResponse)
def admin_login(
    body: AdminLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    client_ip = _client_ip(request)

    # Rate limit
    rl_svc = RateLimitService(db)
    try:
        rl_svc.check_admin_login(
            client_ip, body.email,
            limit=_settings.rate_limit_admin_login_per_5m,
            window_seconds=300,
        )
    except RateLimitError:
        audit_event(
            "admin_login_rate_limited",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            db=db,
        )
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")

    # Authenticate
    auth_svc = AuthService(db)
    try:
        result = auth_svc.login(
            body.email, body.password,
            user_agent=request.headers.get("user-agent", ""),
            client_ip=client_ip,
        )
    except AuthError as exc:
        audit_event(
            "admin_login_failed",
            request_id=_request_id(request),
            client_ip=client_ip,
            result="failure",
            reason_code=str(exc.status_code),
            db=db,
        )
        raise HTTPException(status_code=exc.status_code, detail="邮箱或密码错误。") from exc

    user_id = result.get("user_id", "")

    # Verify admin status
    from app.repositories.user_repo import UserRepository
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="邮箱或密码错误。")

    is_admin = user.is_admin or user.email.lower() in _settings.admin_email_list
    if not is_admin:
        audit_event(
            "admin_login_denied",
            request_id=_request_id(request),
            client_ip=client_ip,
            user_id=user_id,
            result="failure",
            reason_code="not_admin",
            db=db,
        )
        raise HTTPException(status_code=403, detail="需要管理员权限。")

    # Issue admin tokens
    access_token = create_admin_access_token(user_id)
    refresh_str, jti, expires_at = create_admin_refresh_token(user_id)
    jti_h = hash_jti(jti)

    rt = RefreshToken(
        id=str(uuid4()),
        user_id=user_id,
        jti_hash=jti_h,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent", ""),
        client_ip=client_ip,
    )
    token_repo = RefreshTokenRepository(db)
    token_repo.create(rt)

    _set_admin_cookies(response, access_token, refresh_str)

    audit_event(
        "admin_login_success",
        request_id=_request_id(request),
        client_ip=client_ip,
        user_id=user_id,
        db=db,
    )
    ActivityService(db).record(user_id, "admin_login", request)

    return AdminMeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
    )


@router.post("/refresh")
def admin_refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token_str = request.cookies.get(_settings.admin_refresh_cookie_name)
    if not refresh_token_str:
        raise HTTPException(status_code=401, detail="未提供 Refresh Cookie。")

    try:
        payload = decode_token(refresh_token_str, "admin_refresh")
    except TokenError as exc:
        _clear_admin_cookies(response)
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    jti = payload.get("jti", "")
    jti_h = hash_jti(jti)
    token_repo = RefreshTokenRepository(db)
    stored = token_repo.get_by_jti_hash(jti_h)

    if stored is None or stored.revoked_at is not None:
        _clear_admin_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh token 无效或已被撤销。")

    if stored.expires_at < utc_now():
        _clear_admin_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh token 已过期。")

    user_id = stored.user_id

    # Revoke old refresh token
    token_repo.update(stored, {"last_used_at": utc_now()})
    token_repo.revoke(stored, reason="rotated")

    # Issue new tokens
    new_access = create_admin_access_token(user_id)
    new_refresh_str, new_jti, new_expires = create_admin_refresh_token(user_id)
    new_jti_h = hash_jti(new_jti)

    new_rt = RefreshToken(
        id=str(uuid4()),
        user_id=user_id,
        jti_hash=new_jti_h,
        expires_at=new_expires,
        user_agent=request.headers.get("user-agent", ""),
        client_ip=_client_ip(request),
    )
    token_repo.create(new_rt)
    token_repo.update(stored, {"replaced_by_id": new_rt.id})

    _set_admin_cookies(response, new_access, new_refresh_str)
    return {"ok": True}


@router.post("/logout")
def admin_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token_str = request.cookies.get(_settings.admin_refresh_cookie_name)
    if refresh_token_str:
        try:
            payload = decode_token(refresh_token_str, "admin_refresh")
            jti = payload.get("jti", "")
            jti_h = hash_jti(jti)
            token_repo = RefreshTokenRepository(db)
            stored = token_repo.get_by_jti_hash(jti_h)
            if stored and stored.revoked_at is None:
                token_repo.revoke(stored, reason="logout")
        except TokenError:
            pass

    _clear_admin_cookies(response)
    return {"ok": True}


@router.get("/me", response_model=AdminMeResponse)
def admin_me(
    admin_user: User = Depends(get_current_user_from_admin_cookie),
):
    return AdminMeResponse(
        id=admin_user.id,
        email=admin_user.email,
        display_name=admin_user.display_name,
    )
