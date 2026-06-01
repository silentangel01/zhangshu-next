"""Admin global search API — search across users, feedback, and announcements."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permission
from app.core.admin_permissions import SEARCH_GLOBAL, USERS_SENSITIVE_VIEW, has_permission
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.services.admin_search_service import AdminSearchError, AdminSearchService

router = APIRouter(prefix="/api/admin/search", tags=["admin-search"])

_settings = get_settings()


@router.get("")
def global_search(
    q: str = Query(min_length=1, max_length=100, description="Search keyword"),
    admin: User = Depends(require_admin_permission(SEARCH_GLOBAL)),
    db: Session = Depends(get_db),
):
    """Search across users, feedback tickets, and announcements.

    Validation, limits, and email masking are handled by
    :class:`AdminSearchService`. Feedback description is never returned.
    """
    can_view_sensitive = has_permission(admin, USERS_SENSITIVE_VIEW, _settings)
    service = AdminSearchService(db, can_view_sensitive=can_view_sensitive)
    try:
        return service.search(q)
    except AdminSearchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
