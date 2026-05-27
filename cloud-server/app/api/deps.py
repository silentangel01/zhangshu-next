"""Dependency injection for API routes."""

from __future__ import annotations

import logging

from fastapi import Cookie, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.token_service import TokenError, decode_token

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)
_settings = get_settings()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="未提供认证令牌。")

    token = credentials.credentials
    try:
        payload = decode_token(token, "access")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的 Token。")

    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在。")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="账号已被禁用。")

    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Return the current user if a valid Bearer token is present, else None.

    - No Authorization header → returns None (anonymous).
    - Invalid or expired token → raises 401 (do not silently ignore bad auth).
    """
    if credentials is None:
        return None

    token = credentials.credentials
    try:
        payload = decode_token(token, "access")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的 Token。")

    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在。")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="账号已被禁用。")

    return user


def require_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be an administrator.

    A user is admin if:
    - ``user.is_admin`` is True, OR
    - ``user.email`` is in the ``ADMIN_EMAILS`` whitelist.
    """
    if user.is_admin:
        return user
    if user.email.lower() in _settings.admin_email_list:
        return user
    raise HTTPException(status_code=403, detail="需要管理员权限。")


def get_current_user_from_admin_cookie(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Extract admin user from HttpOnly access token cookie.

    Falls back to Bearer token for testing convenience.
    """
    token = request.cookies.get(_settings.admin_cookie_name)

    # Fallback: Bearer token (for tests and API tools)
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(status_code=401, detail="未提供管理员认证。")

    try:
        payload = decode_token(token, "admin_access")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="无效的管理员 Token。")

    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="管理员用户不存在或已被禁用。")

    is_admin = user.is_admin or user.email.lower() in _settings.admin_email_list
    if not is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限。")

    return user


def require_admin_user_cookie_or_bearer(
    user: User = Depends(get_current_user_from_admin_cookie),
) -> User:
    """Alias for get_current_user_from_admin_cookie — explicit admin requirement."""
    return user
