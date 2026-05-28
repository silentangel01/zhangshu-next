"""Admin global search API — search across users, feedback, and announcements."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user_cookie_or_bearer
from app.db.session import get_db
from app.models.announcement import Announcement
from app.models.feedback_ticket import FeedbackTicket
from app.models.user import User

router = APIRouter(prefix="/api/admin/search", tags=["admin-search"])

_MAX_RESULTS_PER_TYPE = 10


@router.get("")
def global_search(
    q: str = Query(min_length=1, max_length=100, description="Search keyword"),
    _admin: User = Depends(require_admin_user_cookie_or_bearer),
    db: Session = Depends(get_db),
):
    """Search across users, feedback tickets, and announcements. Admin-only."""
    pattern = f"%{q}%"

    # Users
    user_rows = list(
        db.scalars(
            select(User.id, User.email, User.display_name)
            .where(
                User.deleted_at.is_(None),
                or_(
                    User.email.ilike(pattern),
                    User.display_name.ilike(pattern),
                ),
            )
            .order_by(User.created_at.desc())
            .limit(_MAX_RESULTS_PER_TYPE)
        )
    )
    users = [
        {"id": r.id, "email": r.email, "display_name": r.display_name}
        for r in user_rows
    ]

    # Feedback
    fb_rows = list(
        db.scalars(
            select(FeedbackTicket.id, FeedbackTicket.title, FeedbackTicket.status)
            .where(
                FeedbackTicket.deleted_at.is_(None),
                or_(
                    FeedbackTicket.title.ilike(pattern),
                    FeedbackTicket.description.ilike(pattern),
                ),
            )
            .order_by(FeedbackTicket.created_at.desc())
            .limit(_MAX_RESULTS_PER_TYPE)
        )
    )
    feedback = [
        {"id": r.id, "title": r.title, "status": r.status}
        for r in fb_rows
    ]

    # Announcements
    ann_rows = list(
        db.scalars(
            select(Announcement.id, Announcement.title, Announcement.status)
            .where(Announcement.title.ilike(pattern))
            .order_by(Announcement.created_at.desc())
            .limit(_MAX_RESULTS_PER_TYPE)
        )
    )
    announcements = [
        {"id": r.id, "title": r.title, "status": r.status}
        for r in ann_rows
    ]

    return {
        "users": users,
        "feedback": feedback,
        "announcements": announcements,
    }
