"""Service layer for cloud backup operations.

Coordinates between BackupService (local zip generation), CloudApiClient
(remote upload), and the local CloudProjectLink / CloudBackupRecord tables.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.infrastructure.cloud_api_client import (
    CloudApiClient,
    CloudApiError,
    CloudApiNotConfiguredError,
)
from app.models.cloud_backup_record import CloudBackupRecord
from app.models.cloud_project_link import CloudProjectLink
from app.repositories.cloud_backup_record_repo import CloudBackupRecordRepository
from app.repositories.cloud_project_link_repo import CloudProjectLinkRepository
from app.services.backup_service import BackupService
from app.services.cloud_auth_service import CloudAuthService

logger = logging.getLogger(__name__)


class CloudBackupError(Exception):
    """Raised when a cloud backup operation fails."""

    def __init__(
        self,
        message: str,
        error_kind: str = "",
        suggestion: str = "",
    ):
        super().__init__(message)
        self.error_kind = error_kind
        self.suggestion = suggestion


class CloudBackupService:
    """Manages cloud backup upload, listing, and restore."""

    def __init__(self, db: Session):
        self._db = db
        self._link_repo = CloudProjectLinkRepository(db)
        self._record_repo = CloudBackupRecordRepository(db)
        self._backup_svc = BackupService(db)
        self._auth_svc = CloudAuthService(db)

    # ── Helpers ───────────────────────────────────────────────────

    def _require_cloud_user_id(self) -> str:
        """Return the current cloud user ID or raise if not logged in."""
        uid = self._auth_svc.get_cloud_user_id()
        if not uid:
            raise CloudBackupError("请先登录章枢云账户。")
        return uid

    # ── Enable / Status ───────────────────────────────────────────

    def enable_cloud(
        self, project_id: str, cloud_project_id: str | None = None
    ) -> CloudProjectLink:
        cloud_user_id = self._require_cloud_user_id()

        existing = self._link_repo.get_by_project(project_id, cloud_user_id)
        if existing is not None:
            return existing

        if not cloud_project_id:
            try:
                from app.models.project import Project

                project = self._db.get(Project, project_id)
                title = project.title if project else "未命名项目"
                result = self._auth_svc.call_with_refresh(
                    lambda c: c.create_cloud_project(title)
                )
                cloud_project_id = str(result.get("id", ""))
            except CloudApiError as exc:
                raise CloudBackupError(
                    f"创建云端项目失败：{exc}",
                    error_kind=exc.error_kind,
                    suggestion=exc.suggestion,
                ) from exc
            except Exception as exc:
                raise CloudBackupError(f"创建云端项目失败：{exc}") from exc
        else:
            # Phase 3: Validate project identity before linking
            from app.services.cloud_sync_service import CloudSyncError, CloudSyncService

            try:
                sync_svc = CloudSyncService(self._db)
                sync_svc.validate_link_existing_project(
                    project_id, cloud_project_id, cloud_user_id
                )
            except CloudSyncError as exc:
                raise CloudBackupError(
                    str(exc),
                    error_kind=exc.error_kind,
                    suggestion=exc.suggestion,
                ) from exc

        link = CloudProjectLink(
            id=str(uuid4()),
            project_id=project_id,
            cloud_project_id=cloud_project_id,
            cloud_user_id=cloud_user_id,
            cloud_enabled=True,
            provider="zhangshu",
            status="active",
        )
        return self._link_repo.create(link)

    def get_status(self, project_id: str) -> dict:
        cloud_user_id = self._auth_svc.get_cloud_user_id()

        if not cloud_user_id:
            # Not logged in — cloud features hidden
            return self._empty_status()

        link = self._link_repo.get_by_project(project_id, cloud_user_id)
        if link is None:
            return self._empty_status()

        return {
            "cloud_enabled": link.cloud_enabled,
            "cloud_project_id": link.cloud_project_id,
            "provider": link.provider,
            "last_backup_at": link.last_backup_at,
            "last_restore_at": link.last_restore_at,
            "status": link.status,
            "last_error": link.last_error,
        }

    @staticmethod
    def _empty_status() -> dict:
        return {
            "cloud_enabled": False,
            "cloud_project_id": None,
            "provider": "zhangshu",
            "last_backup_at": None,
            "last_restore_at": None,
            "status": "inactive",
            "last_error": None,
        }

    # ── Backup ────────────────────────────────────────────────────

    def trigger_backup(self, project_id: str) -> CloudBackupRecord:
        cloud_user_id = self._require_cloud_user_id()

        link = self._link_repo.get_by_project(project_id, cloud_user_id)
        if link is None:
            raise CloudBackupError("请先为该项目启用云端保存。")

        record = CloudBackupRecord(
            id=str(uuid4()),
            project_id=project_id,
            cloud_user_id=cloud_user_id,
            filename="",
            status="pending",
        )
        record = self._record_repo.create(record)

        try:
            content, filename = self._backup_svc.build_project_backup_bytes(
                project_id
            )
            checksum = hashlib.sha256(content).hexdigest()

            record.filename = filename
            record.size_bytes = len(content)
            record.checksum_sha256 = checksum
            self._record_repo.update(
                record,
                {
                    "filename": filename,
                    "size_bytes": len(content),
                    "checksum_sha256": checksum,
                },
                commit=False,
            )

            # Use call_with_refresh for the initial cloud call to handle token expiry
            _cpid = link.cloud_project_id
            _fname = filename
            _size = len(content)
            init_result = self._auth_svc.call_with_refresh(
                lambda c: c.init_backup_upload(_cpid, _fname, _size)
            )
            upload_url = str(init_result.get("upload_url", ""))
            upload_id = str(init_result.get("upload_id", ""))

            # Upload to OSS via presigned URL (no bearer token needed)
            client = self._auth_svc.get_api_client()
            client.upload_backup(upload_url, content)

            # Complete backup goes to cloud API (needs token refresh)
            _cpid2 = link.cloud_project_id
            _uid = upload_id
            _cs = checksum
            complete_result = self._auth_svc.call_with_refresh(
                lambda c: c.complete_backup(_cpid2, _uid, _cs)
            )
            cloud_backup_id = str(complete_result.get("id", ""))
            object_key = str(complete_result.get("object_key", ""))

            now = datetime.now(timezone.utc)
            self._record_repo.update(
                record,
                {
                    "cloud_backup_id": cloud_backup_id,
                    "object_key": object_key,
                    "status": "success",
                    "uploaded_at": now,
                },
            )
            self._link_repo.update(
                link,
                {
                    "last_backup_at": now,
                    "last_error": None,
                    "updated_at": now,
                },
            )
        except (CloudApiError, CloudApiNotConfiguredError) as exc:
            self._record_repo.update(
                record,
                {
                    "status": "failed",
                    "error_message": str(exc),
                },
            )
            self._link_repo.update(
                link,
                {
                    "last_error": str(exc),
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            kind = getattr(exc, "error_kind", "")
            suggestion = getattr(exc, "suggestion", "")
            raise CloudBackupError(
                str(exc), error_kind=kind, suggestion=suggestion
            ) from exc
        except Exception as exc:
            self._record_repo.update(
                record,
                {
                    "status": "failed",
                    "error_message": str(exc),
                },
            )
            raise CloudBackupError(f"备份失败：{exc}") from exc

        return record

    # ── List / Restore ────────────────────────────────────────────

    def list_backups(self, project_id: str) -> list[CloudBackupRecord]:
        cloud_user_id = self._auth_svc.get_cloud_user_id()
        if not cloud_user_id:
            return []
        return self._record_repo.list_by_project(project_id, cloud_user_id)

    def restore_backup(self, project_id: str, record_id: str) -> dict:
        cloud_user_id = self._require_cloud_user_id()

        record = self._record_repo.get(record_id)
        if (
            record is None
            or record.project_id != project_id
            or record.cloud_user_id != cloud_user_id
        ):
            raise CloudBackupError("备份记录不存在。")

        if record.status != "success" or not record.cloud_backup_id:
            raise CloudBackupError("该备份记录不可恢复。")

        link = self._link_repo.get_by_project(project_id, cloud_user_id)
        if link is None:
            raise CloudBackupError("请先为该项目启用云端保存。")

        try:
            _cpid = link.cloud_project_id
            _bid = record.cloud_backup_id
            download_info = self._auth_svc.call_with_refresh(
                lambda c: c.get_backup_download_url(_cpid, _bid)
            )
            download_url = str(download_info.get("download_url", ""))

            import httpx

            with httpx.Client(timeout=120.0, trust_env=False) as http_client:
                response = http_client.get(download_url)
                response.raise_for_status()
                backup_bytes = response.content
        except Exception as exc:
            raise CloudBackupError(f"下载云端备份失败：{exc}") from exc

        try:
            report = self._backup_svc.restore_project_backup(backup_bytes)
        except Exception as exc:
            raise CloudBackupError(f"恢复备份失败：{exc}") from exc

        now = datetime.now(timezone.utc)
        self._link_repo.update(link, {"last_restore_at": now, "updated_at": now})

        return {
            "project_id": report.project_id,
            "project_title": report.project_title,
            "counts": {
                "volumes": report.counts.volumes,
                "chapters": report.counts.chapters,
                "materials": report.counts.materials,
            },
            "warnings": report.warnings,
            "errors": report.errors,
        }
