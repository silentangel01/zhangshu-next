"""Admin user management service — user listing, detail, and management actions."""

from __future__ import annotations

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.models.cloud_backup import CloudBackup
from app.models.cloud_project import CloudProject
from app.models.feedback_ticket import FeedbackTicket
from app.models.refresh_token import RefreshToken
from app.models.user import User, utc_now
from app.models.user_activity_event import UserActivityEvent
from app.schemas.admin_user import (
    AdminRecentActivity,
    AdminRecentFeedback,
    AdminUserDetail,
    AdminUserListItem,
    AdminUserListResponse,
)

from app.core.admin_permissions import ALL_ROLES, ROLE_OWNER


class AdminUserService:
    def __init__(self, db: Session):
        self._db = db

    def list_users(
        self,
        keyword: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AdminUserListResponse:
        query = select(User).where(User.deleted_at.is_(None))
        count_query = select(func.count()).select_from(User).where(
            User.deleted_at.is_(None)
        )

        if keyword:
            pattern = f"%{keyword}%"
            keyword_filter = or_(
                User.email.ilike(pattern),
                User.display_name.ilike(pattern),
            )
            query = query.where(keyword_filter)
            count_query = count_query.where(keyword_filter)

        if status == "active":
            query = query.where(User.is_active.is_(True))
            count_query = count_query.where(User.is_active.is_(True))
        elif status == "inactive":
            query = query.where(User.is_active.is_(False))
            count_query = count_query.where(User.is_active.is_(False))

        total = self._db.scalar(count_query) or 0

        users = list(
            self._db.scalars(
                query.order_by(User.created_at.desc()).offset(offset).limit(limit)
            )
        )

        items = []
        for u in users:
            project_count = self._db.scalar(
                select(func.count())
                .select_from(CloudProject)
                .where(
                    CloudProject.owner_id == u.id,
                    CloudProject.deleted_at.is_(None),
                )
            ) or 0

            # Backup count via projects owned by this user
            backup_count = self._db.scalar(
                select(func.count())
                .select_from(CloudBackup)
                .join(CloudProject, CloudBackup.project_id == CloudProject.id)
                .where(
                    CloudProject.owner_id == u.id,
                    CloudBackup.deleted_at.is_(None),
                )
            ) or 0

            feedback_count = self._db.scalar(
                select(func.count())
                .select_from(FeedbackTicket)
                .where(
                    FeedbackTicket.user_id == u.id,
                    FeedbackTicket.deleted_at.is_(None),
                )
            ) or 0

            items.append(
                AdminUserListItem(
                    id=u.id,
                    email=u.email,
                    display_name=u.display_name,
                    is_active=u.is_active,
                    is_admin=u.is_admin,
                    admin_role=u.admin_role,
                    created_at=u.created_at,
                    last_login_at=u.last_login_at,
                    last_seen_at=u.last_seen_at,
                    login_count=u.login_count or 0,
                    cloud_project_count=project_count,
                    cloud_backup_count=backup_count,
                    feedback_count=feedback_count,
                )
            )

        return AdminUserListResponse(items=items, total=total)

    def get_user_detail(self, user_id: str) -> AdminUserDetail | None:
        user = self._db.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        if user is None:
            return None

        project_count = self._db.scalar(
            select(func.count())
            .select_from(CloudProject)
            .where(
                CloudProject.owner_id == user.id,
                CloudProject.deleted_at.is_(None),
            )
        ) or 0

        backup_count = self._db.scalar(
            select(func.count())
            .select_from(CloudBackup)
            .join(CloudProject, CloudBackup.project_id == CloudProject.id)
            .where(
                CloudProject.owner_id == user.id,
                CloudBackup.deleted_at.is_(None),
            )
        ) or 0

        total_storage = self._db.scalar(
            select(func.coalesce(func.sum(CloudBackup.size_bytes), 0))
            .join(CloudProject, CloudBackup.project_id == CloudProject.id)
            .where(
                CloudProject.owner_id == user.id,
                CloudBackup.deleted_at.is_(None),
                CloudBackup.status == "completed",
            )
        ) or 0

        feedback_count = self._db.scalar(
            select(func.count())
            .select_from(FeedbackTicket)
            .where(
                FeedbackTicket.user_id == user.id,
                FeedbackTicket.deleted_at.is_(None),
            )
        ) or 0

        recent_activity = [
            AdminRecentActivity(event_type=e.event_type, created_at=e.created_at)
            for e in self._db.scalars(
                select(UserActivityEvent)
                .where(UserActivityEvent.user_id == user.id)
                .order_by(UserActivityEvent.created_at.desc())
                .limit(10)
            )
        ]

        recent_feedback = [
            AdminRecentFeedback(
                id=f.id, title=f.title, status=f.status, created_at=f.created_at
            )
            for f in self._db.scalars(
                select(FeedbackTicket)
                .where(
                    FeedbackTicket.user_id == user.id,
                    FeedbackTicket.deleted_at.is_(None),
                )
                .order_by(FeedbackTicket.created_at.desc())
                .limit(5)
            )
        ]

        return AdminUserDetail(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            signature=user.signature,
            is_active=user.is_active,
            is_admin=user.is_admin,
            admin_role=user.admin_role,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            last_seen_at=user.last_seen_at,
            login_count=user.login_count or 0,
            password_changed_at=user.password_changed_at,
            cloud_project_count=project_count,
            cloud_backup_count=backup_count,
            total_storage_bytes=total_storage,
            feedback_count=feedback_count,
            recent_activity=recent_activity,
            recent_feedback=recent_feedback,
        )

    # ── Management actions ──────────────────────────────────────────────

    def _count_active_owners(self) -> int:
        """Count users who are active and have the owner role (or is_admin bootstrap)."""
        from app.core.config import get_settings

        settings = get_settings()

        # Count users with explicit admin_role = "owner" who are active
        explicit_owners = self._db.scalar(
            select(func.count()).select_from(User).where(
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.admin_role == ROLE_OWNER,
            )
        ) or 0

        # Also count bootstrap admins (is_admin=True with no explicit role)
        bootstrap_owners = self._db.scalar(
            select(func.count()).select_from(User).where(
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.is_admin.is_(True),
                User.admin_role.is_(None),
            )
        ) or 0

        # Also count users whose email is in ADMIN_EMAILS and are active
        if settings.admin_email_list:
            email_owners = self._db.scalar(
                select(func.count()).select_from(User).where(
                    User.deleted_at.is_(None),
                    User.is_active.is_(True),
                    User.admin_role.is_(None),
                    User.is_admin.is_(False),
                    func.lower(User.email).in_(
                        [e.lower() for e in settings.admin_email_list]
                    ),
                )
            ) or 0
        else:
            email_owners = 0

        return explicit_owners + bootstrap_owners + email_owners

    def _is_effective_owner(self, user: User) -> bool:
        """Check if a user is effectively an owner (explicit or bootstrap)."""
        from app.core.config import get_settings

        settings = get_settings()
        if user.admin_role == ROLE_OWNER:
            return True
        if user.is_admin and not user.admin_role:
            return True
        if user.email.lower() in settings.admin_email_list and not user.admin_role:
            return True
        return False

    def toggle_active(self, user_id: str, *, actor_id: str = "") -> User | None:
        """Toggle a user's ``is_active`` flag. Returns the updated user or None.

        Raises:
            ValueError: If attempting to disable the last active owner.
        """
        user = self._db.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        if user is None:
            return None

        # If disabling an owner, check last-owner protection
        if user.is_active and self._is_effective_owner(user):
            owner_count = self._count_active_owners()
            if owner_count <= 1:
                raise ValueError("不能禁用最后一个管理员（owner）。")

        user.is_active = not user.is_active
        user.updated_at = utc_now()
        self._db.commit()
        self._db.refresh(user)

        # When disabling a user, also revoke their refresh tokens
        if not user.is_active:
            now = utc_now()
            self._db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None),
                    RefreshToken.expires_at > now,
                )
                .values(revoked_at=now, revoked_reason="admin_disable_user")
            )
            self._db.commit()

        return user

    def force_logout(
        self, user_id: str, *, actor_id: str = ""
    ) -> tuple[int, bool]:
        """Revoke all unexpired refresh tokens for a user.

        Returns:
            Tuple of (count_revoked, target_is_admin).
        """
        now = utc_now()

        # Check if target is an admin
        target = self._db.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        target_is_admin = False
        if target:
            target_is_admin = (
                target.is_admin
                or bool(target.admin_role)
                or target.email.lower()
                in {e.lower() for e in self._get_admin_emails()}
            )

        result = self._db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .values(revoked_at=now, revoked_reason="admin_force_logout")
        )
        self._db.commit()
        return result.rowcount, target_is_admin

    def change_admin_role(
        self,
        user_id: str,
        new_role: str | None,
        *,
        actor_id: str = "",
    ) -> User | None:
        """Change a user's admin_role. Returns the updated user or None.

        Raises:
            ValueError: If the new role is invalid, or if removing the last owner.
        """
        if new_role is not None and new_role not in ALL_ROLES:
            raise ValueError(f"无效的角色: {new_role}")

        user = self._db.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        if user is None:
            return None

        # If removing owner role from an effective owner, check last-owner protection
        if self._is_effective_owner(user) and new_role != ROLE_OWNER:
            owner_count = self._count_active_owners()
            if owner_count <= 1:
                raise ValueError("不能移除最后一个管理员（owner）的角色。")

        user.admin_role = new_role
        user.updated_at = utc_now()
        self._db.commit()
        self._db.refresh(user)

        # Revoke all refresh tokens after role change — force re-login
        now = utc_now()
        self._db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .values(revoked_at=now, revoked_reason="admin_role_changed")
        )
        self._db.commit()

        return user

    def _get_admin_emails(self) -> list[str]:
        from app.core.config import get_settings

        return get_settings().admin_email_list
