"""Admin user management API — listing, detail, and management actions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user_cookie_or_bearer
from app.core.audit import audit_event
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_user import AdminUserDetail, AdminUserListResponse
from app.services.admin_user_service import AdminUserService

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


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
    _admin: User = Depends(require_admin_user_cookie_or_bearer),
    db: Session = Depends(get_db),
):
    service = AdminUserService(db)
    return service.list_users(
        keyword=keyword, status=status, limit=limit, offset=offset
    )


@router.get("/{user_id}", response_model=AdminUserDetail)
def get_user_detail(
    user_id: str,
    _admin: User = Depends(require_admin_user_cookie_or_bearer),
    db: Session = Depends(get_db),
):
    service = AdminUserService(db)
    detail = service.get_user_detail(user_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="用户不存在。")
    return detail


@router.post("/{user_id}/toggle-active")
def toggle_user_active(
    user_id: str,
    admin: User = Depends(require_admin_user_cookie_or_bearer),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Toggle a user's active status. Admin-only."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的状态。")

    service = AdminUserService(db)
    user = service.toggle_active(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在。")

    audit_event(
        "admin_toggle_user_active",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={"target_user_id": user_id},
        db=db,
    )
    return {"id": user.id, "is_active": user.is_active}


@router.post("/{user_id}/force-logout")
def force_logout_user(
    user_id: str,
    admin: User = Depends(require_admin_user_cookie_or_bearer),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Revoke all active sessions for a user. Admin-only."""
    service = AdminUserService(db)
    count = service.force_logout(user_id)

    audit_event(
        "admin_force_logout",
        request_id=_request_id(request),
        client_ip=_client_ip(request),
        user_id=admin.id,
        result="success",
        extra={"target_user_id": user_id, "tokens_revoked": count},
        db=db,
    )
    return {"ok": True, "tokens_revoked": count}
