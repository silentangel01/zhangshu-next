"""Admin role management API — permission matrix and role changes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permission
from app.core.admin_permissions import (
    ADMIN_ROLES_MANAGE,
    ROLE_OWNER,
    effective_admin_role,
    get_permission_matrix,
    permissions_for_role,
)
from app.core.audit import audit_event
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_role import (
    AdminPermissionMatrixResponse,
    AdminRoleUpdateRequest,
)
from app.services.admin_user_service import AdminUserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/roles", tags=["admin-roles"])

_settings = get_settings()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.get("/permissions", response_model=AdminPermissionMatrixResponse)
def get_permissions(
    admin: User = Depends(require_admin_permission("dashboard:view")),
):
    """Return the role → permissions matrix and current user's role/permissions."""
    matrix = get_permission_matrix()
    role = effective_admin_role(admin, _settings)
    perms = sorted(permissions_for_role(role))
    return AdminPermissionMatrixResponse(
        roles=matrix,
        current_user_role=role,
        current_user_permissions=perms,
    )


@router.patch("/users/{user_id}/admin-role")
def change_user_admin_role(
    user_id: str,
    body: AdminRoleUpdateRequest,
    admin: User = Depends(require_admin_permission(ADMIN_ROLES_MANAGE)),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Change a user's admin role. Only owner can grant or revoke owner role."""
    # Cannot change own role
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色。")

    # Confirm text must match for this high-risk action
    if body.confirm_text != "确认变更角色":
        raise HTTPException(
            status_code=400,
            detail='确认文本不正确，请输入"确认变更角色"。',
        )

    # Only owner can grant or revoke owner role
    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=404, detail="用户不存在。")

    admin_role = effective_admin_role(admin, _settings)
    target_role = effective_admin_role(target_user, _settings)

    # If assigning owner or removing owner, actor must be owner
    if body.admin_role == ROLE_OWNER or target_role == ROLE_OWNER:
        if admin_role != ROLE_OWNER:
            raise HTTPException(
                status_code=403,
                detail="只有 owner 可以授予或移除 owner 角色。",
            )

    service = AdminUserService(db)
    old_role = target_role

    try:
        user = service.change_admin_role(
            user_id, body.admin_role, actor_id=admin.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在。")

    new_role = effective_admin_role(user, _settings)

    audit_event(
        "admin_role_changed",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={
            "target_user_id": user_id,
            "old_role": old_role or "none",
            "new_role": new_role or "none",
            "action_reason": body.reason,
            "risk_level": "critical",
            "permission": ADMIN_ROLES_MANAGE,
        },
        db=db,
    )

    return {
        "id": user.id,
        "admin_role": user.admin_role,
        "effective_role": new_role,
    }
