"""Usage and quota calculation service."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.cloud_backup import CloudBackup
from app.models.cloud_project import CloudProject
from app.models.user import utc_now


class UsageService:
    """Calculate per-user storage, backup counts, and rate limit usage."""

    def __init__(self, db: Session):
        self._db = db
        self._settings = get_settings()

    def get_usage(self, user_id: str) -> dict:
        """Return the current usage snapshot for the user."""
        project_ids = select(CloudProject.id).where(
            CloudProject.owner_id == user_id,
            CloudProject.deleted_at.is_(None),
        )

        # Storage used (sum of successful backup sizes)
        storage_used = self._db.scalar(
            select(func.coalesce(func.sum(CloudBackup.size_bytes), 0)).where(
                CloudBackup.status == "success",
                CloudBackup.deleted_at.is_(None),
                CloudBackup.project_id.in_(project_ids),
            )
        ) or 0

        # Backup count (successful, non-deleted)
        backup_count = self._db.scalar(
            select(func.count()).select_from(CloudBackup).where(
                CloudBackup.status == "success",
                CloudBackup.deleted_at.is_(None),
                CloudBackup.project_id.in_(project_ids),
            )
        ) or 0

        # Backup init count in the last hour
        since = utc_now() - timedelta(hours=1)
        init_last_hour = self._db.scalar(
            select(func.count()).select_from(CloudBackup).where(
                CloudBackup.created_at >= since,
                CloudBackup.project_id.in_(project_ids),
            )
        ) or 0

        return {
            "storage_used_bytes": int(storage_used),
            "storage_quota_bytes": self._settings.default_storage_quota_bytes,
            "backup_count": int(backup_count),
            "backup_count_quota": self._settings.default_backup_count_quota,
            "backup_init_used_last_hour": int(init_last_hour),
            "backup_init_limit_per_hour": self._settings.rate_limit_backup_init_per_hour,
            "max_backup_size_bytes": self._settings.max_backup_size_bytes,
        }
