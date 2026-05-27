"""Admin dashboard metrics aggregation service.

All queries go through repositories — no raw SQL in the API layer.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cloud_backup import CloudBackup
from app.models.cloud_project import CloudProject
from app.models.feedback_ticket import FeedbackTicket
from app.models.user import User, utc_now
from app.repositories.user_activity_repo import UserActivityRepository


class AdminMetricsService:
    def __init__(self, db: Session):
        self._db = db
        self._activity_repo = UserActivityRepository(db)

    def get_summary(self) -> dict:
        now = utc_now()
        hours_24 = now - timedelta(hours=24)
        days_7 = now - timedelta(days=7)
        days_30 = now - timedelta(days=30)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_users = self._db.scalar(select(func.count()).select_from(User)) or 0
        active_24h = self._activity_repo.count_distinct_users_since(hours_24)
        active_7d = self._activity_repo.count_distinct_users_since(days_7)
        active_30d = self._activity_repo.count_distinct_users_since(days_30)

        today_registrations = self._db.scalar(
            select(func.count()).select_from(User).where(User.created_at >= today_start)
        ) or 0

        total_cloud_projects = (
            self._db.scalar(select(func.count()).select_from(CloudProject)) or 0
        )
        total_cloud_backups = (
            self._db.scalar(select(func.count()).select_from(CloudBackup)) or 0
        )
        total_storage_bytes = (
            self._db.scalar(
                select(func.coalesce(func.sum(CloudBackup.size_bytes), 0))
            )
            or 0
        )

        open_feedback = self._db.scalar(
            select(func.count())
            .select_from(FeedbackTicket)
            .where(
                FeedbackTicket.status.in_(["open", "in_progress"]),
                FeedbackTicket.deleted_at.is_(None),
            )
        ) or 0

        urgent_feedback = self._db.scalar(
            select(func.count())
            .select_from(FeedbackTicket)
            .where(
                FeedbackTicket.priority.in_(["urgent", "high"]),
                FeedbackTicket.status.in_(["open", "in_progress"]),
                FeedbackTicket.deleted_at.is_(None),
            )
        ) or 0

        return {
            "total_users": total_users,
            "active_24h": active_24h,
            "active_7d": active_7d,
            "active_30d": active_30d,
            "today_registrations": today_registrations,
            "total_cloud_projects": total_cloud_projects,
            "total_cloud_backups": total_cloud_backups,
            "total_storage_bytes": total_storage_bytes,
            "open_feedback": open_feedback,
            "urgent_feedback": urgent_feedback,
        }

    def get_activity_series(self, days: int = 14) -> dict:
        now = utc_now()
        since = now - timedelta(days=days)

        daily_active = self._activity_repo.count_by_day("login_success", since, days)
        daily_registrations = self._activity_repo.count_by_day(
            "user_registered", since, days
        )
        daily_feedback = self._activity_repo.count_by_day(
            "feedback_created", since, days
        )
        daily_backups = self._activity_repo.count_by_day(
            "backup_complete", since, days
        )

        return {
            "days": days,
            "daily_active": daily_active,
            "daily_registrations": daily_registrations,
            "daily_feedback": daily_feedback,
            "daily_backups": daily_backups,
        }

    def get_feedback_stats(self) -> dict:
        status_rows = self._db.execute(
            select(FeedbackTicket.status, func.count())
            .where(FeedbackTicket.deleted_at.is_(None))
            .group_by(FeedbackTicket.status)
        ).all()
        by_status = {row[0]: row[1] for row in status_rows}

        category_rows = self._db.execute(
            select(FeedbackTicket.category, func.count())
            .where(FeedbackTicket.deleted_at.is_(None))
            .group_by(FeedbackTicket.category)
        ).all()
        by_category = {row[0]: row[1] for row in category_rows}

        return {
            "by_status": by_status,
            "by_category": by_category,
        }
