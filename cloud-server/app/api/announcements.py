"""Public announcement API — read-only, no auth required."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.announcement import AnnouncementListResponse
from app.services.announcement_service import AnnouncementService

router = APIRouter(prefix="/api/announcements", tags=["announcements"])


@router.get("", response_model=AnnouncementListResponse)
def list_announcements(
    platform: str | None = Query(default=None, description="Filter by platform"),
    app_version: str | None = Query(default=None, description="Client app version"),
    db: Session = Depends(get_db),
) -> AnnouncementListResponse:
    """Return currently active published announcements.

    No authentication required — visible to all clients including anonymous users.
    """
    svc = AnnouncementService(db)
    return svc.list_active(platform=platform, app_version=app_version)
