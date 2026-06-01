"""Admin user management API — listing, detail, and management actions."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permission
from app.core.admin_permissions import (
    ROLE_OWNER,
    USERS_FORCE_LOGOUT,
    USERS_TOGGLE_ACTIVE,
    USERS_VIEW,
    effective_admin_role,
)
from app.core.audit import audit_event
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_role import AdminRiskActionRequest
from app.schemas.admin_user import AdminUserDetail, AdminUserListResponse
from app.services.admin_user_service import AdminUserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])

_settings = get_settings()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.get("", response_model=AdminUserListResponse)
def list_users(
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin_permission(USERS_VIEW)),
    db: Session = Depends(get_db),
):
    service = AdminUserService(db)
    return service.list_users(
        keyword=keyword, status=status, limit=limit, offset=offset
    )


@router.get("/{user_id}", response_model=AdminUserDetail)
def get_user_detail(
    user_id: str,
    admin: User = Depends(require_admin_permission(USERS_VIEW)),
    db: Session = Depends(get_db),
    request: Request = None,
):
    service = AdminUserService(db)
    detail = service.get_user_detail(user_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="用户不存在。")

    # Audit: viewing user detail
    audit_event(
        "admin_user_detail_viewed",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={"target_user_id": user_id},
        db=db,
    )
    return detail


@router.post("/{user_id}/toggle-active")
def toggle_user_active(
    user_id: str,
    body: AdminRiskActionRequest,
    admin: User = Depends(require_admin_permission(USERS_TOGGLE_ACTIVE)),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Toggle a user's active status. Requires reason and permission."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的状态。")

    service = AdminUserService(db)
    try:
        user = service.toggle_active(user_id, actor_id=admin.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在。")

    action = "disable" if not user.is_active else "enable"
    audit_event(
        "admin_toggle_user_active",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={
            "target_user_id": user_id,
            "action_reason": body.reason,
            "risk_level": "high",
            "new_status": "active" if user.is_active else "disabled",
        },
        db=db,
    )
    return {"id": user.id, "is_active": user.is_active, "action": action}


@router.post("/{user_id}/force-logout")
def force_logout_user(
    user_id: str,
    body: AdminRiskActionRequest,
    admin: User = Depends(require_admin_permission(USERS_FORCE_LOGOUT)),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Revoke all active sessions for a user. Requires reason and permission."""
    service = AdminUserService(db)
    count, target_is_admin = service.force_logout(user_id, actor_id=admin.id)

    # If target is admin, only owner can force-logout
    if target_is_admin:
        admin_role = effective_admin_role(admin, _settings)
        if admin_role != ROLE_OWNER:
            raise HTTPException(
                status_code=403,
                detail="只有 owner 角色可以强制下线其他管理员。",
            )

    audit_event(
        "admin_force_logout",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={
            "target_user_id": user_id,
            "tokens_revoked": count,
            "action_reason": body.reason,
            "risk_level": "high",
        },
        db=db,
    )
    return {"ok": True, "tokens_revoked": count}
