"""Admin dashboard API routes — summary, activity, feedback stats."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permission
from app.core.admin_permissions import DASHBOARD_VIEW
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_dashboard import (
    ActivitySeriesResponse,
    DashboardSummaryResponse,
    FeedbackStatsResponse,
)
from app.services.admin_metrics_service import AdminMetricsService

router = APIRouter(prefix="/api/admin/dashboard", tags=["admin-dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_summary(
    _admin: User = Depends(require_admin_permission(DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    service = AdminMetricsService(db)
    return service.get_summary()


@router.get("/activity", response_model=ActivitySeriesResponse)
def get_activity(
    days: int = Query(default=14, ge=1, le=90),
    _admin: User = Depends(require_admin_permission(DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    service = AdminMetricsService(db)
    return service.get_activity_series(days=days)


@router.get("/feedback-stats", response_model=FeedbackStatsResponse)
def get_feedback_stats(
    _admin: User = Depends(require_admin_permission(DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    service = AdminMetricsService(db)
    return service.get_feedback_stats()
