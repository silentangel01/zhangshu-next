"""Admin user management API — read-only listing and detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user_cookie_or_bearer
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_user import AdminUserDetail, AdminUserListResponse
from app.services.admin_user_service import AdminUserService

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


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
