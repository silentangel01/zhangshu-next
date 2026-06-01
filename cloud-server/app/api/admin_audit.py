"""Admin audit log query API — permission-graded with IP masking."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permission
from app.core.admin_permissions import AUDIT_VIEW
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/api/admin/audit", tags=["admin-audit"])


def _mask_ip(ip: str) -> str:
    """Mask an IP address for display: 192.168.1.xxx."""
    if not ip:
        return ""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
    # IPv6 or other formats — just show first segment
    if ":" in ip:
        first = ip.split(":")[0]
        return f"{first}:xxxx"
    return "***"


@router.get("")
def list_audit_logs(
    event: str | None = Query(default=None, description="Filter by event type"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin_permission(AUDIT_VIEW)),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Paginated audit log query. Requires ``audit:view`` permission.

    IPs are masked for privacy. Full IP is never exposed via this endpoint.
    """
    query = db.query(AuditLog)

    if event:
        query = query.filter(AuditLog.event == event)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    items = (
        query.order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": [
            {
                "id": row.id,
                "event": row.event,
                "request_id": row.request_id,
                "client_ip": _mask_ip(row.client_ip),
                "user_id": row.user_id,
                "project_id": row.project_id,
                "backup_id": row.backup_id,
                "result": row.result,
                "reason_code": row.reason_code,
                "extra_json": row.extra_json,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in items
        ],
        "total": total,
    }
