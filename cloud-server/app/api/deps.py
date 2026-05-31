"""Dependency injection for API routes."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.admin_permissions import effective_admin_role, has_permission
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.token_service import TokenError, decode_token

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)
_settings = get_settings()

# UTC+8 for naive datetime comparison (matches model utc_now())
_CST = timezone(timedelta(hours=8))


def _check_token_not_pre_password_change(
    payload: dict, user: User
) -> None:
    """Reject tokens issued before the user's last password change.

    Compares the JWT ``iat`` claim against ``user.password_changed_at``.
    Both are normalized to naive UTC+8 for SQLite compatibility.
    """
    if not user.password_changed_at:
        return

    iat = payload.get("iat")
    if iat is None:
        return

    # iat from PyJWT may be int (Unix timestamp) or datetime
    if isinstance(iat, (int, float)):
        token_issued = datetime.fromtimestamp(iat, tz=_CST).replace(tzinfo=None)
    elif isinstance(iat, datetime):
        token_issued = iat.replace(tzinfo=None) if iat.tzinfo else iat
    else:
        return

    pwd_changed = user.password_changed_at
    if pwd_changed.tzinfo:
        pwd_changed = pwd_changed.replace(tzinfo=None)

    # Truncate both to second precision for fair comparison.
    # JWT iat is in whole seconds; DB datetimes may have microseconds.
    token_issued = token_issued.replace(microsecond=0)
    pwd_changed = pwd_changed.replace(microsecond=0)

    if token_issued < pwd_changed:
        raise HTTPException(
            status_code=401,
            detail="密码已修改，请重新登录。",
        )


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

    _check_token_not_pre_password_change(payload, user)

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

    Bearer token fallback is only allowed when:
    - environment is not "production", OR
    - ``admin_allow_bearer_fallback`` is explicitly True.
    In production with fallback disabled, missing cookie → immediate 401.
    """
    token = request.cookies.get(_settings.admin_cookie_name)

    # Fallback: Bearer token (for tests and API tools)
    if not token:
        bearer_allowed = (
            _settings.environment != "production"
            or _settings.admin_allow_bearer_fallback
        )
        if bearer_allowed:
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
    if not is_admin and not user.admin_role:
        raise HTTPException(status_code=403, detail="需要管理员权限。")

    _check_token_not_pre_password_change(payload, user)

    return user


def require_admin_user_cookie_or_bearer(
    user: User = Depends(get_current_user_from_admin_cookie),
) -> User:
    """Alias for get_current_user_from_admin_cookie — explicit admin requirement."""
    return user


def require_admin_permission(
    permission: str,
) -> Callable[..., User]:
    """Return a FastAPI dependency that checks a specific admin permission.

    Usage in a router::

        @router.get("/items")
        def list_items(
            admin: User = Depends(require_admin_permission("items:view")),
        ): ...

    Raises 403 if the current admin user lacks the required permission.
    """

    def _checker(
        user: User = Depends(require_admin_user_cookie_or_bearer),
    ) -> User:
        if not has_permission(user, permission, _settings):
            role = effective_admin_role(user, _settings)
            raise HTTPException(
                status_code=403,
                detail=f"权限不足：需要 {permission}（当前角色: {role or 'none'}）。",
            )
        return user

    return _checker
