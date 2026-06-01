"""Admin monitoring API — Aliyun service health overview."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_admin_permission
from app.core.admin_permissions import MONITORING_VIEW
from app.core.config import get_settings
from app.models.user import User
from app.schemas.admin_monitoring import MonitoringOverviewResponse
from app.services.admin_monitoring_service import AdminMonitoringService

router = APIRouter(prefix="/api/admin/monitoring", tags=["admin-monitoring"])


@router.get("/overview", response_model=MonitoringOverviewResponse)
def get_monitoring_overview(
    _admin: User = Depends(require_admin_permission(MONITORING_VIEW)),
):
    """Return cached Aliyun service metrics (billing, OSS, SWAS)."""
    service = AdminMonitoringService(get_settings())
    return service.get_overview()


@router.post("/refresh", response_model=MonitoringOverviewResponse)
def refresh_monitoring(
    module: str | None = Query(default=None),
    _admin: User = Depends(require_admin_permission(MONITORING_VIEW)),
):
    """Force-refresh one module (billing/oss/server) or all."""
    service = AdminMonitoringService(get_settings())
    return service.refresh(module=module)
