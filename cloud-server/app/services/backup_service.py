"""Backup management service with quota, rate limiting, and cleanup."""

from __future__ import annotations

import logging
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import is_valid_sha256_hex
from app.infrastructure.oss_storage import OSSError, OSSStorage
from app.models.cloud_backup import CloudBackup
from app.models.cloud_project import CloudProject
from app.models.user import utc_now
from app.repositories.cloud_backup_repo import CloudBackupRepository
from app.services.project_service import ProjectError, ProjectService

logger = logging.getLogger(__name__)

# Stale uploads older than this are candidates for cleanup
_STALE_UPLOAD_HOURS = 6


class BackupError(Exception):
    """Raised for backup operation failures."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class BackupService:
    def __init__(self, db: Session, oss: OSSStorage | None = None):
        self._db = db
        self._repo = CloudBackupRepository(db)
        self._project_svc = ProjectService(db)
        self._oss = oss or OSSStorage()
        self._settings = get_settings()

    def _ensure_oss_configured(self) -> None:
        if not self._oss.is_configured:
            raise BackupError(
                "云服务 OSS 存储未配置，请联系管理员设置 OSS_ACCESS_KEY_ID 和 OSS_ACCESS_KEY_SECRET。",
                status_code=503,
            )

    # ------------------------------------------------------------------
    # Quota and rate limit checks
    # ------------------------------------------------------------------

    def _check_storage_quota(self, user_id: str, additional_bytes: int) -> None:
        """Raise BackupError if adding *additional_bytes* exceeds the user quota."""
        quota = self._settings.default_storage_quota_bytes
        total_used = self._db.scalar(
            select(func.coalesce(func.sum(CloudBackup.size_bytes), 0)).where(
                CloudBackup.status == "success",
                CloudBackup.deleted_at.is_(None),
                CloudBackup.project_id.in_(
                    select(CloudProject.id).where(CloudProject.owner_id == user_id)
                ),
            )
        ) or 0

        if total_used + additional_bytes > quota:
            max_mb = quota // (1024 * 1024)
            raise BackupError(
                f"云备份空间已达上限（{max_mb} MB），请删除旧备份后重试。"
            )

    def _check_count_quota(self, user_id: str) -> None:
        """Raise BackupError if the user has reached the backup count limit."""
        quota = self._settings.default_backup_count_quota

        count = self._db.scalar(
            select(func.count()).select_from(CloudBackup).where(
                CloudBackup.status == "success",
                CloudBackup.deleted_at.is_(None),
                CloudBackup.project_id.in_(
                    select(CloudProject.id).where(CloudProject.owner_id == user_id)
                ),
            )
        ) or 0

        if count >= quota:
            raise BackupError(
                f"备份数量已达上限（{quota} 个），请删除旧备份后重试。"
            )

    def _check_rate_limit(self, user_id: str) -> None:
        """Raise BackupError if the user exceeded hourly backup init rate."""
        limit = self._settings.rate_limit_backup_init_per_hour
        since = utc_now() - timedelta(hours=1)

        count = self._db.scalar(
            select(func.count()).select_from(CloudBackup).where(
                CloudBackup.created_at >= since,
                CloudBackup.project_id.in_(
                    select(CloudProject.id).where(CloudProject.owner_id == user_id)
                ),
            )
        ) or 0

        if count >= limit:
            raise BackupError(
                f"备份上传频率过高（每小时最多 {limit} 次），请稍后再试。",
                status_code=429,
            )

    # ------------------------------------------------------------------
    # Stale upload cleanup
    # ------------------------------------------------------------------

    def cleanup_stale_uploads(self) -> int:
        """Mark uploading records older than threshold as failed.

        Returns the number of records cleaned.
        """
        cutoff = utc_now() - timedelta(hours=_STALE_UPLOAD_HOURS)

        stale = list(
            self._db.scalars(
                select(CloudBackup).where(
                    CloudBackup.status == "uploading",
                    CloudBackup.created_at < cutoff,
                )
            ).all()
        )

        for backup in stale:
            self._repo.update(
                backup,
                {"status": "failed", "error_message": "上传超时，系统自动标记失败。"},
            )

        if stale:
            logger.info("Cleaned up %d stale upload records", len(stale))

        return len(stale)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def init_upload(
        self,
        project_id: str,
        user_id: str,
        filename: str,
        size_bytes: int,
    ) -> dict:
        self._ensure_oss_configured()
        project = self._project_svc.get_project_for_user(project_id, user_id)

        if not filename or not filename.strip():
            raise BackupError("文件名不能为空。")
        if size_bytes <= 0:
            raise BackupError("文件大小必须大于 0。")
        if size_bytes > self._settings.max_backup_size_bytes:
            max_mb = self._settings.max_backup_size_bytes // (1024 * 1024)
            raise BackupError(f"文件大小不得超过 {max_mb} MB。")

        # Quota and rate limit checks
        self._check_storage_quota(user_id, size_bytes)
        self._check_count_quota(user_id)
        self._check_rate_limit(user_id)

        backup_id = str(uuid4())
        upload_id = str(uuid4())
        object_key = self._oss.build_object_key(
            user_id, project.id, backup_id, filename
        )
        expires_seconds = self._settings.oss_presigned_url_expire_seconds
        upload_expires_at = utc_now() + timedelta(seconds=expires_seconds)

        try:
            upload_url = self._oss.generate_put_url(
                object_key, expires_seconds, content_type="application/zip"
            )
        except OSSError as exc:
            raise BackupError(f"生成上传链接失败：{exc}", status_code=500) from exc

        backup = CloudBackup(
            id=backup_id,
            project_id=project.id,
            object_key=object_key,
            filename=filename.strip(),
            size_bytes=size_bytes,
            status="uploading",
            upload_id=upload_id,
            upload_expires_at=upload_expires_at,
        )
        self._repo.create(backup)

        return {"upload_url": upload_url, "upload_id": upload_id}

    def complete_upload(
        self,
        project_id: str,
        user_id: str,
        upload_id: str,
        checksum_sha256: str,
    ) -> dict:
        self._ensure_oss_configured()
        project = self._project_svc.get_project_for_user(project_id, user_id)

        if not is_valid_sha256_hex(checksum_sha256):
            raise BackupError("checksum_sha256 格式无效，应为 64 位十六进制字符串。")

        backup = self._repo.get_by_upload_id(upload_id)
        if backup is None or backup.project_id != project.id:
            raise BackupError("upload_id 无效或不属于该项目。", status_code=404)

        if backup.status != "uploading":
            raise BackupError("该上传任务状态异常。")

        if backup.upload_expires_at < utc_now():
            self._repo.update(
                backup,
                {"status": "failed", "error_message": "上传链接已过期。"},
            )
            raise BackupError("上传链接已过期，请重新初始化上传。")

        # Verify OSS object exists and size matches
        try:
            meta = self._oss.head_object(backup.object_key)
        except OSSError:
            self._repo.update(
                backup,
                {"status": "failed", "error_message": "OSS 对象不存在。"},
            )
            raise BackupError("上传文件未在 OSS 中找到。")

        if meta.get("size") != backup.size_bytes:
            self._repo.update(
                backup,
                {
                    "status": "failed",
                    "error_message": f"文件大小不匹配：预期 {backup.size_bytes}，实际 {meta.get('size')}",
                },
            )
            raise BackupError("上传文件大小与声明不一致。")

        now = utc_now()
        self._repo.update(
            backup,
            {
                "status": "success",
                "checksum_sha256": checksum_sha256.lower(),
                "uploaded_at": now,
            },
        )

        return {"id": backup.id, "object_key": backup.object_key}

    def list_backups(self, project_id: str, user_id: str) -> tuple[list[CloudBackup], int]:
        project = self._project_svc.get_project_for_user(project_id, user_id)
        items = self._repo.get_by_project(project.id)
        total = self._repo.count_by_project(project.id)
        return items, total

    def get_download_url(
        self, project_id: str, user_id: str, backup_id: str
    ) -> str:
        self._ensure_oss_configured()
        project = self._project_svc.get_project_for_user(project_id, user_id)
        backup = self._repo.get_by_id(backup_id)

        if backup is None or backup.project_id != project.id:
            raise BackupError("备份不存在。", status_code=404)

        if backup.status != "success":
            raise BackupError("该备份尚未完成上传。")

        try:
            return self._oss.generate_get_url(backup.object_key)
        except OSSError as exc:
            raise BackupError(
                f"生成下载链接失败：{exc}", status_code=500
            ) from exc

    def delete_backup(
        self, project_id: str, user_id: str, backup_id: str
    ) -> None:
        self._ensure_oss_configured()
        project = self._project_svc.get_project_for_user(project_id, user_id)
        backup = self._repo.get_by_id(backup_id)

        if backup is None or backup.project_id != project.id:
            raise BackupError("备份不存在。", status_code=404)

        # Delete OSS object first
        try:
            self._oss.delete_object(backup.object_key)
        except OSSError:
            logger.warning(
                "Failed to delete OSS object %s, proceeding with DB soft delete.",
                backup.object_key,
            )

        # Soft delete in DB
        self._repo.soft_delete(backup)
