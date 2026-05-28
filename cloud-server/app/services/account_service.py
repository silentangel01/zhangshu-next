"""Account management service: profile, password, sessions, export, deletion."""

from __future__ import annotations

import json
import logging
import secrets
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import audit_event
from app.core.security import (
    hash_password,
    sha256_text,
    validate_password_strength,
    verify_password,
)
from app.infrastructure.oss_storage import OSSError, OSSStorage
from app.models.account_deletion_request import AccountDeletionRequest
from app.models.cloud_backup import CloudBackup
from app.models.cloud_project import CloudProject
from app.models.feedback_ticket import FeedbackTicket
from app.models.refresh_token import RefreshToken
from app.models.user import User, utc_now
from app.repositories.feedback_repo import FeedbackRepository
from app.repositories.refresh_token_repo import RefreshTokenRepository
from app.repositories.user_repo import UserRepository
from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)

# Avatar upload limits
AVATAR_ALLOWED_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
AVATAR_MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB

# Deletion confirmation text the user must type
DELETION_CONFIRMATION_TEXT = "DELETE MY CLOUD DATA"

# How long a deletion request stays valid (10 minutes)
_DELETION_REQUEST_TTL_MINUTES = 10


class AccountError(Exception):
    """Raised for account operation failures."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class AccountService:
    def __init__(self, db: Session, oss: OSSStorage | None = None):
        self._db = db
        self._user_repo = UserRepository(db)
        self._token_repo = RefreshTokenRepository(db)
        self._feedback_repo = FeedbackRepository(db)
        self._oss = oss or OSSStorage()

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, user_id: str) -> dict:
        user = self._get_active_user(user_id)
        avatar_url = None
        if user.avatar_object_key:
            try:
                avatar_url = self._oss.generate_get_url(
                    user.avatar_object_key, expires_seconds=3600
                )
            except OSSError:
                logger.warning("Failed to generate avatar URL for user %s", user_id)

        return {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "signature": user.signature,
            "avatar_url": avatar_url,
            "avatar_updated_at": user.avatar_updated_at,
            "password_changed_at": user.password_changed_at,
            "created_at": user.created_at,
        }

    def update_profile(
        self,
        user_id: str,
        display_name: str | None = None,
        signature: str | None = None,
    ) -> dict:
        user = self._get_active_user(user_id)
        updates: dict = {"updated_at": utc_now()}

        if display_name is not None:
            stripped = display_name.strip()
            if not stripped:
                raise AccountError("显示名不能为空。")
            if len(stripped) > 128:
                raise AccountError("显示名不得超过 128 个字符。")
            updates["display_name"] = stripped

        if signature is not None:
            sig = signature.strip()
            if len(sig) > 160:
                raise AccountError("签名不得超过 160 个字符。")
            updates["signature"] = sig or None

        self._user_repo.update(user, updates)
        return self.get_profile(user_id)

    # ------------------------------------------------------------------
    # Password
    # ------------------------------------------------------------------

    def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> dict:
        user = self._get_active_user(user_id)

        if not verify_password(old_password, user.password_hash):
            raise AccountError("当前密码不正确。")

        if old_password == new_password:
            raise AccountError("新密码不能与当前密码相同。")

        pw_error = validate_password_strength(new_password)
        if pw_error:
            raise AccountError(pw_error)

        self._user_repo.update(user, {
            "password_hash": hash_password(new_password),
            "password_changed_at": utc_now(),
            "updated_at": utc_now(),
        })

        # Revoke all refresh tokens — force re-login
        revoked = self._revoke_all_tokens(user_id, reason="password_changed")

        return {
            "message": f"密码已修改，{revoked} 个会话已退出登录。",
        }

    # ------------------------------------------------------------------
    # Avatar
    # ------------------------------------------------------------------

    def init_avatar_upload(
        self,
        user_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
    ) -> dict:
        user = self._get_active_user(user_id)

        if content_type not in AVATAR_ALLOWED_TYPES:
            raise AccountError(
                f"头像只支持 PNG、JPEG、WebP 格式，当前: {content_type}"
            )
        if size_bytes > AVATAR_MAX_SIZE_BYTES:
            raise AccountError(
                f"头像大小不得超过 {AVATAR_MAX_SIZE_BYTES // (1024*1024)} MB。"
            )

        avatar_id = str(uuid4())
        object_key = self._oss.build_avatar_object_key(user_id, avatar_id, filename)
        upload_url = self._oss.generate_put_url(
            object_key, expires_seconds=600, content_type=content_type
        )

        from datetime import timedelta
        expires_at = utc_now() + timedelta(minutes=10)

        return {
            "upload_url": upload_url,
            "upload_id": avatar_id,
            "expires_at": expires_at,
            "object_key": object_key,
            "content_type": content_type,
        }

    def complete_avatar_upload(
        self,
        user_id: str,
        object_key: str,
        content_type: str,
    ) -> dict:
        user = self._get_active_user(user_id)

        # Delete old avatar object if exists
        old_key = user.avatar_object_key
        if old_key:
            try:
                self._oss.delete_object(old_key)
            except OSSError:
                logger.warning("Failed to delete old avatar: %s", old_key)

        now = utc_now()
        self._user_repo.update(user, {
            "avatar_object_key": object_key,
            "avatar_content_type": content_type,
            "avatar_updated_at": now,
            "updated_at": now,
        })

        avatar_url = None
        try:
            avatar_url = self._oss.generate_get_url(object_key, expires_seconds=3600)
        except OSSError:
            pass

        return {
            "avatar_url": avatar_url,
            "avatar_updated_at": now,
        }

    def delete_avatar(self, user_id: str) -> dict:
        user = self._get_active_user(user_id)

        if user.avatar_object_key:
            try:
                self._oss.delete_object(user.avatar_object_key)
            except OSSError:
                logger.warning("Failed to delete avatar: %s", user.avatar_object_key)

        self._user_repo.update(user, {
            "avatar_object_key": None,
            "avatar_content_type": None,
            "avatar_updated_at": None,
            "updated_at": utc_now(),
        })

        return {"avatar_url": None, "avatar_updated_at": None}

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def list_sessions(self, user_id: str) -> list[dict]:
        self._get_active_user(user_id)
        tokens = list(self._db.scalars(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > utc_now(),
            )
            .order_by(RefreshToken.created_at.desc())
        ).all())

        return [
            {
                "id": t.id,
                "created_at": t.created_at,
                "last_used_at": t.last_used_at,
                "user_agent": t.user_agent,
                "client_ip": t.client_ip,
                "is_current": False,  # Caller can override for current session
            }
            for t in tokens
        ]

    def revoke_session(self, user_id: str, session_id: str) -> None:
        self._get_active_user(user_id)
        token = self._db.scalar(
            select(RefreshToken).where(
                RefreshToken.id == session_id,
                RefreshToken.user_id == user_id,
            )
        )
        if token is None:
            raise AccountError("会话不存在。", status_code=404)

        self._token_repo.revoke(token, reason="user_revoked")

    def revoke_all_sessions(
        self, user_id: str, *, keep_current: bool = False
    ) -> dict:
        self._get_active_user(user_id)
        revoked = self._revoke_all_tokens(user_id, reason="user_revoke_all")
        return {
            "revoked_count": revoked,
            "message": f"已退出 {revoked} 个设备。",
        }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_account_data(self, user_id: str) -> dict:
        user = self._get_active_user(user_id)
        usage_svc = UsageService(self._db)
        usage = usage_svc.get_usage(user_id)

        # Projects
        projects = list(self._db.scalars(
            select(CloudProject).where(
                CloudProject.owner_id == user_id,
                CloudProject.deleted_at.is_(None),
            )
        ).all())

        project_data = []
        for proj in projects:
            backups = list(self._db.scalars(
                select(CloudBackup).where(
                    CloudBackup.project_id == proj.id,
                    CloudBackup.deleted_at.is_(None),
                )
            ).all())
            project_data.append({
                "id": proj.id,
                "title": proj.title,
                "created_at": proj.created_at.isoformat(),
                "backups": [
                    {
                        "id": b.id,
                        "backup_filename": b.filename,
                        "size_bytes": b.size_bytes,
                        "checksum_sha256": b.checksum_sha256,
                        "status": b.status,
                        "created_at": b.created_at.isoformat(),
                        "uploaded_at": b.uploaded_at.isoformat() if b.uploaded_at else None,
                    }
                    for b in backups
                ],
            })

        return {
            "account": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "created_at": user.created_at.isoformat(),
            },
            "usage": usage,
            "projects": project_data,
            "feedback": self._export_feedback_metadata(user_id),
            "exported_at": utc_now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Two-stage deletion
    # ------------------------------------------------------------------

    def request_deletion(self, user_id: str, password: str) -> dict:
        user = self._get_active_user(user_id)

        if not verify_password(password, user.password_hash):
            raise AccountError("密码不正确。", status_code=401)

        # Calculate impact
        project_ids = select(CloudProject.id).where(
            CloudProject.owner_id == user_id,
            CloudProject.deleted_at.is_(None),
        )
        project_count = self._db.scalar(
            select(func.count()).select_from(CloudProject).where(
                CloudProject.owner_id == user_id,
                CloudProject.deleted_at.is_(None),
            )
        ) or 0

        backup_query = select(CloudBackup).where(
            CloudBackup.status == "success",
            CloudBackup.deleted_at.is_(None),
            CloudBackup.project_id.in_(project_ids),
        )
        backups = list(self._db.scalars(backup_query).all())
        backup_count = len(backups)
        total_size = sum(b.size_bytes for b in backups)

        # Generate confirmation token
        token = secrets.token_urlsafe(32)
        token_hash = sha256_text(token)

        expires_at = utc_now() + timedelta(minutes=_DELETION_REQUEST_TTL_MINUTES)

        summary = json.dumps({
            "project_count": project_count,
            "backup_count": backup_count,
            "total_size_bytes": total_size,
        })

        req = AccountDeletionRequest(
            id=str(uuid4()),
            user_id=user_id,
            confirm_token_hash=token_hash,
            summary_json=summary,
            expires_at=expires_at,
        )
        self._db.add(req)

        # Mark user as having requested deletion
        self._user_repo.update(user, {"deletion_requested_at": utc_now()})

        self._db.commit()
        self._db.refresh(req)

        return {
            "request_id": token,  # Plain token returned to client only
            "expires_at": expires_at,
            "project_count": project_count,
            "backup_count": backup_count,
            "total_size_bytes": total_size,
            "confirmation_text": DELETION_CONFIRMATION_TEXT,
        }

    def confirm_deletion(
        self, user_id: str, request_id: str, confirmation_text: str
    ) -> dict:
        user = self._get_active_user(user_id)

        if confirmation_text != DELETION_CONFIRMATION_TEXT:
            raise AccountError("确认文本不正确。")

        # Look up the deletion request by token hash
        token_hash = sha256_text(request_id)
        deletion_req = self._db.scalar(
            select(AccountDeletionRequest).where(
                AccountDeletionRequest.user_id == user_id,
                AccountDeletionRequest.confirm_token_hash == token_hash,
                AccountDeletionRequest.used_at.is_(None),
            )
        )

        if deletion_req is None:
            raise AccountError("删除请求无效或已使用。")

        if deletion_req.expires_at < utc_now():
            raise AccountError("删除请求已过期，请重新发起。")

        # Mark request as used
        deletion_req.used_at = utc_now()
        self._db.commit()

        # --- Execute deletion ---
        project_ids = select(CloudProject.id).where(
            CloudProject.owner_id == user_id,
            CloudProject.deleted_at.is_(None),
        )

        # 1. Delete OSS objects
        backups = list(self._db.scalars(
            select(CloudBackup).where(
                CloudBackup.status == "success",
                CloudBackup.deleted_at.is_(None),
                CloudBackup.project_id.in_(project_ids),
            )
        ).all())

        oss_failures = 0
        for backup in backups:
            try:
                self._oss.delete_object(backup.object_key)
            except OSSError:
                oss_failures += 1
                logger.warning(
                    "Failed to delete OSS object %s during account deletion",
                    backup.object_key,
                )

        # 2. Soft-delete all backups
        now = utc_now()
        deleted_backup_count = 0
        all_backups = list(self._db.scalars(
            select(CloudBackup).where(
                CloudBackup.deleted_at.is_(None),
                CloudBackup.project_id.in_(project_ids),
            )
        ).all())
        for b in all_backups:
            b.deleted_at = now
            deleted_backup_count += 1

        # 3. Soft-delete all projects
        projects = list(self._db.scalars(
            select(CloudProject).where(
                CloudProject.owner_id == user_id,
                CloudProject.deleted_at.is_(None),
            )
        ).all())
        deleted_project_count = len(projects)
        for p in projects:
            p.deleted_at = now

        # 4. Revoke all tokens
        self._revoke_all_tokens(user_id, reason="account_deleted")

        # 5. Handle feedback privacy: anonymize tickets, delete OSS attachments
        feedback_anonymized = self._anonymize_user_feedback(user_id)

        # 6. Anonymize user
        anon_email = f"deleted+{user_id}@deleted.local"
        random_hash = secrets.token_hex(16)
        self._user_repo.update(user, {
            "email": anon_email,
            "display_name": "已删除用户",
            "password_hash": f"DELETED:{random_hash}",
            "is_active": False,
            "deleted_at": now,
            "anonymized_at": now,
        })

        self._db.commit()

        audit_event(
            "account_deleted",
            user_id=user_id,
            result="success" if oss_failures == 0 else "partial",
            reason_code="oss_partial_failure" if oss_failures > 0 else "",
            db=self._db,
        )

        result = {
            "message": "云账号和云端数据已删除。",
            "deleted_projects": deleted_project_count,
            "deleted_backups": deleted_backup_count,
            "feedback_anonymized": feedback_anonymized,
            "oss_failures": oss_failures,
        }

        if oss_failures > 0:
            result["message"] = (
                f"云账号已删除，但有 {oss_failures} 个 OSS 文件删除失败，"
                "管理员将稍后处理。"
            )

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_active_user(self, user_id: str) -> User:
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise AccountError("用户不存在。", status_code=404)
        if user.deleted_at is not None or user.anonymized_at is not None:
            raise AccountError("账号已被删除。", status_code=404)
        return user

    def _revoke_all_tokens(self, user_id: str, *, reason: str) -> int:
        tokens = list(self._db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        ).all())
        for t in tokens:
            self._token_repo.revoke(t, reason=reason, commit=False)
        self._db.commit()
        return len(tokens)

    def _export_feedback_metadata(self, user_id: str) -> list[dict]:
        """Export feedback metadata for the user (no admin notes, no presigned URLs)."""
        tickets = self._feedback_repo.list_tickets(user_id=user_id, limit=1000)
        result = []
        for t in tickets:
            result.append({
                "id": t.id,
                "category": t.category,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "attachment_count": t.attachment_count,
            })
        return result

    def _anonymize_user_feedback(self, user_id: str) -> int:
        """Remove user association from feedback and delete OSS attachments.

        Returns count of anonymized tickets.
        """
        # Delete OSS objects for user's attachments
        attachments = self._feedback_repo.list_user_attachments(user_id)
        for att in attachments:
            try:
                self._oss.delete_object(att.object_key)
            except OSSError:
                logger.warning(
                    "Failed to delete feedback OSS object during account deletion: %s",
                    att.object_key,
                )
            self._feedback_repo.soft_delete_attachment(att, commit=False)

        count = self._feedback_repo.anonymize_user_feedback(user_id, commit=False)
        if attachments or count:
            self._db.commit()
        return count
