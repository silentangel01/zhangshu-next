"""Cloud sync service — orchestrates incremental sync between local and cloud.

This is the main entry point for sync operations. It coordinates:
- CloudAuthService for authentication
- SyncDirtyService for tracking local changes
- SyncSerializer for converting entities to/from sync payloads
- SyncApplyService for applying remote changes locally
- CloudApiClient for communicating with the cloud server
"""

from __future__ import annotations

import logging
import platform
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.infrastructure.cloud_api_client import (
    CloudApiClient,
    CloudApiError,
    CloudApiNotConfiguredError,
)
from app.models.cloud_project_link import CloudProjectLink
from app.models.cloud_sync_state import CloudSyncState
from app.repositories.cloud_project_link_repo import CloudProjectLinkRepository
from app.services.cloud_auth_service import CloudAuthService
from app.services.sync_apply_service import SyncApplyService
from app.services.sync_dirty_service import SyncDirtyService
from app.services.sync_serializer import (
    SYNC_ENTITY_MODELS,
    get_active_entity,
    payload_to_json,
    serialize_entity,
)

logger = logging.getLogger(__name__)

# Maximum changes per push/pull batch
MAX_CHANGES_PER_BATCH = 200

# Maximum pull iterations in a single sync run to avoid infinite loops
MAX_PULL_ITERATIONS = 10


class CloudSyncError(Exception):
    """Raised when a cloud sync operation fails."""

    def __init__(
        self,
        message: str,
        error_kind: str = "",
        suggestion: str = "",
    ):
        super().__init__(message)
        self.error_kind = error_kind
        self.suggestion = suggestion


def _generate_device_id() -> str:
    """Generate a stable device identifier based on hostname and platform."""
    hostname = platform.node() or "unknown"
    system = platform.system() or "unknown"
    return f"{system}-{hostname}"


def _normalize_remote_backup_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a backup item from the remote API.

    The remote ``BackupResponse`` schema uses ``id``, while legacy/local
    structures may use ``cloud_backup_id``. This helper accepts both.
    Returns ``None`` when the item is not a usable (status=success) backup.
    """
    backup_id = str(item.get("id") or item.get("cloud_backup_id") or "")
    status = str(item.get("status") or "")
    if status != "success" or not backup_id:
        return None
    return {
        "id": backup_id,
        "status": status,
        "created_at": item.get("created_at") or "",
        "uploaded_at": item.get("uploaded_at") or "",
        "filename": item.get("filename") or "",
    }


class CloudSyncService:
    """Orchestrates incremental cloud sync for local projects."""

    def __init__(self, db: Session):
        self._db = db
        self._auth_svc = CloudAuthService(db)
        self._dirty_svc = SyncDirtyService(db)
        self._apply_svc = SyncApplyService(db)
        self._link_repo = CloudProjectLinkRepository(db)

    # ── Status ────────────────────────────────────────────────────

    def get_status(self, project_id: str) -> dict[str, Any]:
        """Return sync status for a project."""
        logged_in = self._auth_svc.is_logged_in()
        cloud_user_id = self._auth_svc.get_cloud_user_id()

        link = None
        sync_state = None

        if cloud_user_id:
            link = self._link_repo.get_by_project(project_id, cloud_user_id)
            if link is not None:
                sync_state = self._get_sync_state(project_id, cloud_user_id)

        pending_count = self._dirty_svc.count_dirty(project_id)

        if sync_state is not None:
            return {
                "cloud_logged_in": logged_in,
                "cloud_enabled": link is not None and link.cloud_enabled,
                "pending_count": pending_count,
                "last_cursor": sync_state.last_cursor,
                "last_sync_at": sync_state.last_sync_at,
                "last_error": sync_state.last_error,
                "status": sync_state.status,
                "auto_sync_enabled": sync_state.auto_sync_enabled,
                "cloud_project_id": sync_state.cloud_project_id,
                "device_id": sync_state.device_id,
            }

        return {
            "cloud_logged_in": logged_in,
            "cloud_enabled": False,
            "pending_count": pending_count,
            "last_cursor": 0,
            "last_sync_at": None,
            "last_error": None,
            "status": "not_linked",
            "auto_sync_enabled": True,
            "cloud_project_id": None,
            "device_id": "",
        }

    # ── Ensure sync state ─────────────────────────────────────────

    def ensure_sync_state(self, project_id: str) -> CloudSyncState:
        """Ensure a sync state exists for the project, creating link if needed."""
        cloud_user_id = self._require_cloud_user()

        link = self._link_repo.get_by_project(project_id, cloud_user_id)
        if link is None:
            # Create a cloud project and link
            client = self._auth_svc.get_api_client()

            from app.services.project_service import ProjectService
            project_svc = ProjectService(self._db)
            project = project_svc.get_project(project_id)

            try:
                cloud_project = self._auth_svc.call_with_refresh(
                    lambda c: c.create_cloud_project(project.title)
                )
                cloud_project_id = cloud_project["id"]
            except CloudApiError as exc:
                raise CloudSyncError(
                    f"创建云端项目失败：{exc}",
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
            self._link_repo.create(link)

        sync_state = self._get_sync_state(project_id, cloud_user_id)
        if sync_state is not None:
            return sync_state

        # Create new sync state
        sync_state = CloudSyncState(
            id=str(uuid4()),
            project_id=project_id,
            cloud_user_id=cloud_user_id,
            cloud_project_id=link.cloud_project_id,
            device_id=_generate_device_id(),
            last_cursor=0,
            status="idle",
            auto_sync_enabled=True,
        )
        self._db.add(sync_state)
        self._db.commit()
        self._db.refresh(sync_state)
        return sync_state

    # ── Run sync ──────────────────────────────────────────────────

    def run_sync(self, project_id: str) -> dict[str, Any]:
        """Execute a full sync cycle: push dirty records, then pull remote changes."""
        start_time = time.monotonic()
        errors: list[str] = []
        pushed_count = 0
        pulled_count = 0
        conflict_count = 0

        cloud_user_id = self._require_cloud_user()
        sync_state = self.ensure_sync_state(project_id)
        link = self._link_repo.get_by_project(project_id, cloud_user_id)
        if link is None:
            raise CloudSyncError(
                "项目未关联云端，请先启用云同步。",
                error_kind="not_linked",
            )

        cloud_project_id = sync_state.cloud_project_id
        old_cursor = sync_state.last_cursor

        # Mark as syncing
        sync_state.status = "syncing"
        sync_state.updated_at = datetime.now(timezone.utc)
        self._db.commit()

        try:
            # Phase 1: Push dirty records
            pushed_count, push_conflicts, push_errors = self._push_dirty(
                project_id, cloud_project_id, sync_state.device_id
            )
            conflict_count += push_conflicts
            errors.extend(push_errors)

            # Phase 2: Pull remote changes
            new_cursor, pulled_count, pull_errors = self._pull_remote(
                project_id, cloud_project_id, old_cursor
            )
            errors.extend(pull_errors)

            # Update sync state
            sync_state.last_cursor = new_cursor
            sync_state.last_sync_at = datetime.now(timezone.utc)
            sync_state.status = "idle"
            sync_state.last_error = "; ".join(errors) if errors else None
            sync_state.updated_at = datetime.now(timezone.utc)
            self._db.commit()

        except Exception as exc:
            sync_state.status = "error"
            sync_state.last_error = str(exc)
            sync_state.updated_at = datetime.now(timezone.utc)
            self._db.commit()
            raise CloudSyncError(
                f"同步失败：{exc}",
                error_kind="sync_failed",
                suggestion="请稍后重试。如果问题持续，请检查网络连接。",
            ) from exc

        duration_ms = int((time.monotonic() - start_time) * 1000)

        return {
            "pushed": pushed_count,
            "pulled": pulled_count,
            "new_cursor": sync_state.last_cursor,
            "conflicts": conflict_count,
            "errors": errors,
            "duration_ms": duration_ms,
        }

    # ── Pull only ─────────────────────────────────────────────────

    def pull_only(self, project_id: str) -> dict[str, Any]:
        """Pull remote changes without pushing local dirty records."""
        cloud_user_id = self._require_cloud_user()
        sync_state = self._get_sync_state(project_id, cloud_user_id)
        if sync_state is None:
            raise CloudSyncError(
                "项目尚未启用云同步。",
                error_kind="not_linked",
            )

        new_cursor, pulled_count, errors = self._pull_remote(
            project_id, sync_state.cloud_project_id, sync_state.last_cursor
        )

        sync_state.last_cursor = new_cursor
        sync_state.last_sync_at = datetime.now(timezone.utc)
        sync_state.last_error = "; ".join(errors) if errors else None
        sync_state.updated_at = datetime.now(timezone.utc)
        self._db.commit()

        return {
            "pulled": pulled_count,
            "new_cursor": new_cursor,
            "errors": errors,
        }

    # ── Import cloud project ──────────────────────────────────────

    def import_cloud_project(self, cloud_project_id: str) -> dict[str, Any]:
        """Import a cloud project to the local database.

        Strategy:
        0. If an active link already exists, return immediately (no duplicate).
        1. Try incremental sync_pull first (preferred, preserves sync cursor).
        2. If no sync data exists, fall back to downloading the latest backup.
        """
        cloud_user_id = self._require_cloud_user()

        # ── Guard: prevent duplicate restore ──
        existing_link = self._link_repo.get_by_cloud_project(
            cloud_project_id, cloud_user_id
        )
        if existing_link is not None:
            # Fetch title from local project
            from app.models.project import Project
            local_project = self._db.get(Project, existing_link.project_id)
            title = local_project.title if local_project else "未命名项目"
            return {
                "local_project_id": existing_link.project_id,
                "title": title,
                "volumes_count": 0,
                "chapters_count": 0,
                "mode": "already_exists",
                "message": "该云端项目已在本机存在，已打开本机项目。",
            }

        # ── Strategy 1: incremental sync pull ──
        all_changes, final_cursor = self._collect_initial_remote_changes(cloud_project_id)

        if all_changes:
            return self._import_from_sync_changes(
                cloud_project_id, cloud_user_id, all_changes, final_cursor
            )

        # ── Strategy 2: fall back to latest backup ──
        return self._import_from_backup(cloud_project_id, cloud_user_id)

    # ── Phase 3: Link existing project helpers ────────────────────

    def _collect_initial_remote_changes(
        self, cloud_project_id: str
    ) -> tuple[list[dict[str, Any]], int]:
        """Collect all remote changes from cursor 0 (used by import and validation)."""
        all_changes: list[dict[str, Any]] = []
        cursor = 0
        final_cursor = 0

        def _do_pull(client: CloudApiClient) -> dict[str, Any]:
            return client.sync_pull(cloud_project_id, cursor, MAX_CHANGES_PER_BATCH)

        for _ in range(MAX_PULL_ITERATIONS):
            result = self._auth_svc.call_with_refresh(_do_pull)
            changes = result.get("changes", [])
            all_changes.extend(changes)
            new_cursor = result.get("new_cursor", cursor)
            has_more = result.get("has_more", False)

            if new_cursor > final_cursor:
                final_cursor = new_cursor

            if not has_more or not changes:
                break
            cursor = new_cursor

        return all_changes, final_cursor

    @staticmethod
    def _find_remote_project_entity_id(changes: list[dict[str, Any]]) -> str | None:
        """Extract the project entity_id from remote changes.

        Returns None if no project entity found.
        Raises CloudSyncError if multiple project entities found (ambiguous).
        """
        project_entities = [
            c for c in changes
            if c.get("entity_type") == "projects" and c.get("action") != "delete"
        ]

        if len(project_entities) > 1:
            raise CloudSyncError(
                "云端数据包含多个项目实体，无法确定关联目标。",
                error_kind="ambiguous_project_identity",
                suggestion="请联系管理员检查云端数据完整性。",
            )

        if not project_entities:
            return None

        return project_entities[0].get("entity_id")

    def validate_link_existing_project(
        self, project_id: str, cloud_project_id: str, cloud_user_id: str
    ) -> None:
        """Validate that linking cloud_project_id to local project_id is safe.

        Raises CloudSyncError if validation fails.
        """
        # Check if cloud_project_id is already linked to another local project
        other_link = self._link_repo.get_by_cloud_project(
            cloud_project_id, cloud_user_id
        )
        if other_link is not None and other_link.project_id != project_id:
            raise CloudSyncError(
                "该云端项目已关联到本机另一个项目。",
                error_kind="cloud_project_already_linked",
                suggestion="该云端项目已在本机存在，请从项目列表打开已有项目，不要重复关联。",
            )

        # Collect remote changes to verify project identity
        try:
            all_changes, _ = self._collect_initial_remote_changes(cloud_project_id)
        except Exception as exc:
            raise CloudSyncError(
                f"无法获取云端项目数据：{exc}",
                error_kind="remote_fetch_failed",
                suggestion="请检查网络连接后重试。",
            ) from exc

        # Empty changes: local project will be the initial source, allow linking
        if not all_changes:
            return

        # Non-empty changes: must have project entity for identity verification
        remote_project_id = self._find_remote_project_entity_id(all_changes)

        if remote_project_id is None:
            raise CloudSyncError(
                "云端增量数据缺少项目身份信息，无法安全关联。",
                error_kind="missing_project_identity",
                suggestion='请联系管理员检查云端数据完整性，或使用「恢复为新项目」功能。',
            )

        # Identity mismatch: reject
        if remote_project_id != project_id:
            raise CloudSyncError(
                '该云端项目属于另一个项目，请使用「恢复为新项目」。',
                error_kind="project_identity_mismatch",
                suggestion='云端项目与当前本地项目不是同一个项目。如需使用云端数据，请从项目列表选择「从云端恢复」。',
            )

        # Identity match: allow linking
        return

    def _import_from_sync_changes(
        self,
        cloud_project_id: str,
        cloud_user_id: str,
        all_changes: list[dict[str, Any]],
        final_cursor: int,
    ) -> dict[str, Any]:
        """Create a local project from incremental sync changes."""
        applied = self._apply_svc.apply_changes(all_changes)

        project_changes = [
            c for c in all_changes
            if c.get("entity_type") == "projects" and c.get("action") != "delete"
        ]
        if not project_changes:
            raise CloudSyncError(
                "该云端项目缺少基本项目信息，无法导入。",
                error_kind="no_project_entity",
                suggestion="请联系管理员检查云端数据完整性。",
            )

        local_project_id = project_changes[0]["entity_id"]
        project_title = project_changes[0].get("data", {}).get("title", "未命名项目")

        link = CloudProjectLink(
            id=str(uuid4()),
            project_id=local_project_id,
            cloud_project_id=cloud_project_id,
            cloud_user_id=cloud_user_id,
            cloud_enabled=True,
            provider="zhangshu",
            status="active",
        )
        self._link_repo.create(link)

        sync_state = CloudSyncState(
            id=str(uuid4()),
            project_id=local_project_id,
            cloud_user_id=cloud_user_id,
            cloud_project_id=cloud_project_id,
            device_id=_generate_device_id(),
            last_cursor=final_cursor,
            last_sync_at=datetime.now(timezone.utc),
            status="idle",
            auto_sync_enabled=True,
        )
        self._db.add(sync_state)
        self._db.commit()

        volumes_count = sum(
            1 for c in all_changes
            if c.get("entity_type") == "volumes" and c.get("action") != "delete"
        )
        chapters_count = sum(
            1 for c in all_changes
            if c.get("entity_type") == "chapters" and c.get("action") != "delete"
        )

        return {
            "local_project_id": local_project_id,
            "title": project_title,
            "volumes_count": volumes_count,
            "chapters_count": chapters_count,
            "mode": "restored_as_new",
        }

    def _import_from_backup(
        self, cloud_project_id: str, cloud_user_id: str
    ) -> dict[str, Any]:
        """Import by downloading and restoring the latest cloud backup."""
        # List remote backups
        def _do_list(client: CloudApiClient) -> dict[str, Any]:
            return client.list_backups(cloud_project_id)

        try:
            backup_list = self._auth_svc.call_with_refresh(_do_list)
        except Exception as exc:
            raise CloudSyncError(
                "该项目暂无增量同步数据，且无法获取云端备份列表。",
                error_kind="backup_list_failed",
                suggestion="请稍后重试，或联系管理员检查云端备份状态。",
            ) from exc

        items = backup_list.get("items", []) if isinstance(backup_list, dict) else backup_list

        # Log diagnostic info (no sensitive data)
        total_count = len(items) if isinstance(items, list) else 0
        status_dist: dict[str, int] = {}
        for raw_item in (items if isinstance(items, list) else []):
            s = str(raw_item.get("status") or "unknown")
            status_dist[s] = status_dist.get(s, 0) + 1
        logger.info(
            "Cloud backup list: %d total items, status distribution: %s",
            total_count,
            status_dist,
        )

        successful: list[dict[str, Any]] = []
        for raw_item in (items if isinstance(items, list) else []):
            normalized = _normalize_remote_backup_item(raw_item)
            if normalized is not None:
                successful.append(normalized)

        logger.info("Cloud backup list: %d usable (status=success) backups", len(successful))

        if not successful:
            raise CloudSyncError(
                "云端项目没有增量同步数据，且未找到状态为 success 的云端备份。",
                error_kind="empty_project",
                suggestion="如果本机备份面板显示已完成，请确认导入弹窗选择的是同一个云端项目。",
            )

        # Sort by uploaded_at (preferred) or created_at descending, take the latest
        successful.sort(
            key=lambda b: b.get("uploaded_at") or b.get("created_at") or "",
            reverse=True,
        )
        latest = successful[0]
        backup_id = latest["id"]

        # Download the backup
        def _do_download(client: CloudApiClient) -> dict[str, Any]:
            return client.get_backup_download_url(cloud_project_id, backup_id)

        try:
            download_info = self._auth_svc.call_with_refresh(_do_download)
            download_url = str(download_info.get("download_url", ""))
        except Exception as exc:
            raise CloudSyncError(
                "获取云端备份下载地址失败。",
                error_kind="download_url_failed",
                suggestion="请稍后重试，或联系管理员。",
            ) from exc

        try:
            import httpx

            with httpx.Client(timeout=120.0, trust_env=False) as http_client:
                response = http_client.get(download_url)
                response.raise_for_status()
                backup_bytes = response.content
        except Exception as exc:
            raise CloudSyncError(
                "下载云端备份失败。",
                error_kind="download_failed",
                suggestion="请检查网络连接后重试。如问题持续，请联系管理员。",
            ) from exc

        # Restore from backup
        from app.services.backup_service import BackupService

        backup_svc = BackupService(self._db)
        try:
            report = backup_svc.restore_project_backup(backup_bytes)
        except Exception as exc:
            raise CloudSyncError(
                f"从云端备份恢复项目失败。",
                error_kind="restore_failed",
                suggestion=f"备份文件可能已损坏。请联系管理员协助处理。",
            ) from exc

        local_project_id = report.project_id

        # Create cloud project link
        link = CloudProjectLink(
            id=str(uuid4()),
            project_id=local_project_id,
            cloud_project_id=cloud_project_id,
            cloud_user_id=cloud_user_id,
            cloud_enabled=True,
            provider="zhangshu",
            status="active",
        )
        self._link_repo.create(link)

        # Create sync state (cursor=0 since we restored from backup, not sync)
        sync_state = CloudSyncState(
            id=str(uuid4()),
            project_id=local_project_id,
            cloud_user_id=cloud_user_id,
            cloud_project_id=cloud_project_id,
            device_id=_generate_device_id(),
            last_cursor=0,
            last_sync_at=datetime.now(timezone.utc),
            status="idle",
            auto_sync_enabled=True,
        )
        self._db.add(sync_state)
        self._db.commit()

        return {
            "local_project_id": local_project_id,
            "title": report.project_title,
            "volumes_count": report.counts.volumes,
            "chapters_count": report.counts.chapters,
            "mode": "restored_as_new",
        }

    # ── List snapshots/conflicts ──────────────────────────────────

    def list_snapshots(
        self, project_id: str, entity_type: str, entity_id: str
    ) -> list[dict[str, Any]]:
        """List cloud snapshots for a specific entity."""
        cloud_user_id = self._require_cloud_user()
        sync_state = self._get_sync_state(project_id, cloud_user_id)
        if sync_state is None:
            return []

        def _do_list(client: CloudApiClient) -> list[dict[str, Any]]:
            return client.list_sync_snapshots(
                sync_state.cloud_project_id, entity_type, entity_id
            )

        return self._auth_svc.call_with_refresh(_do_list)

    def list_conflicts(
        self, project_id: str, resolved: bool = False
    ) -> list[dict[str, Any]]:
        """List cloud conflicts for a project."""
        cloud_user_id = self._require_cloud_user()
        sync_state = self._get_sync_state(project_id, cloud_user_id)
        if sync_state is None:
            return []

        def _do_list(client: CloudApiClient) -> list[dict[str, Any]]:
            return client.list_sync_conflicts(
                sync_state.cloud_project_id, resolved
            )

        return self._auth_svc.call_with_refresh(_do_list)

    # ── Internal: push dirty records ──────────────────────────────

    def _push_dirty(
        self,
        project_id: str,
        cloud_project_id: str,
        device_id: str,
    ) -> tuple[int, int, list[str]]:
        """Push all dirty records for a project. Returns (pushed, conflicts, errors)."""
        dirty_records = self._dirty_svc.list_dirty(project_id, limit=MAX_CHANGES_PER_BATCH)
        if not dirty_records:
            return 0, 0, []

        errors: list[str] = []
        total_pushed = 0
        total_conflicts = 0

        # Build changes from dirty records
        changes: list[dict[str, Any]] = []
        for record in dirty_records:
            entity_type = record.entity_type
            entity_id = record.entity_id
            action = record.action

            if entity_type not in SYNC_ENTITY_MODELS:
                logger.warning(
                    "Skipping dirty record with unknown entity type: %s",
                    entity_type,
                )
                continue

            if action == "upsert":
                entity = get_active_entity(self._db, entity_type, entity_id)
                if entity is None:
                    # Entity was deleted locally after being marked dirty
                    # Skip — the delete dirty record will handle it
                    continue
                data = serialize_entity(entity, entity_type)
                change = {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "action": "upsert",
                    "data": data,
                    "device_id": device_id,
                    "local_version": entity.version if hasattr(entity, "version") else 1,
                    "local_updated_at": (
                        entity.updated_at.isoformat()
                        if hasattr(entity, "updated_at") and entity.updated_at
                        else datetime.now(timezone.utc).isoformat()
                    ),
                }
            elif action == "delete":
                # For delete, send the entity data if available
                entity = get_active_entity(self._db, entity_type, entity_id)
                data = {}
                if entity is not None:
                    data = serialize_entity(entity, entity_type)
                data["deleted_at"] = datetime.now(timezone.utc).isoformat()
                change = {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "action": "delete",
                    "data": data,
                    "device_id": device_id,
                }
            else:
                continue

            changes.append(change)

        if not changes:
            return 0, 0, []

        # Push to cloud
        cursor = 0

        def _do_push(client: CloudApiClient) -> dict[str, Any]:
            return client.sync_push(
                cloud_project_id,
                {"cursor": cursor, "changes": changes},
            )

        try:
            result = self._auth_svc.call_with_refresh(_do_push)

            accepted = result.get("accepted", [])
            rejected = result.get("rejected", [])
            conflicts = result.get("conflicts", [])

            total_pushed = len(accepted)
            total_conflicts = len(conflicts)

            # Remove accepted dirty records
            accepted_entities = [
                (item["entity_type"], item["entity_id"])
                for item in accepted
            ]
            self._dirty_svc.remove_dirty_batch(project_id, accepted_entities)

            # Mark errors on rejected records
            for item in rejected:
                reason = item.get("reason", "unknown rejection reason")
                self._dirty_svc.mark_error(
                    project_id,
                    item["entity_type"],
                    item["entity_id"],
                    reason,
                )
                errors.append(f"{item['entity_type']}/{item['entity_id']}: {reason}")

        except CloudApiError as exc:
            error_msg = f"推送失败：{exc}"
            logger.error(error_msg)
            errors.append(error_msg)

            # Mark all dirty records with error
            for record in dirty_records:
                self._dirty_svc.mark_error(
                    project_id,
                    record.entity_type,
                    record.entity_id,
                    str(exc),
                )

        return total_pushed, total_conflicts, errors

    # ── Internal: pull remote changes ─────────────────────────────

    def _pull_remote(
        self,
        project_id: str,
        cloud_project_id: str,
        cursor: int,
    ) -> tuple[int, int, list[str]]:
        """Pull remote changes and apply locally. Returns (new_cursor, pulled_count, errors)."""
        errors: list[str] = []
        total_pulled = 0
        current_cursor = cursor

        for iteration in range(MAX_PULL_ITERATIONS):
            def _do_pull(client: CloudApiClient) -> dict[str, Any]:
                return client.sync_pull(cloud_project_id, current_cursor, MAX_CHANGES_PER_BATCH)

            try:
                result = self._auth_svc.call_with_refresh(_do_pull)
            except CloudApiError as exc:
                errors.append(f"拉取失败：{exc}")
                break

            changes = result.get("changes", [])
            new_cursor = result.get("new_cursor", current_cursor)
            has_more = result.get("has_more", False)

            if changes:
                # Record which dirty records exist before apply
                pre_apply_dirty = {
                    (r.entity_type, r.entity_id)
                    for r in self._dirty_svc.list_dirty(project_id)
                }

                # Apply remote changes
                apply_result = self._apply_svc.apply_changes(changes)
                total_pulled += apply_result["applied"]

                # Clean up dirty records that were overwritten by remote
                # Only clean if the dirty record was NOT a local modification
                # that predates the remote change (i.e. it was already pushed)
                for change in changes:
                    key = (change["entity_type"], change["entity_id"])
                    if key in pre_apply_dirty:
                        # If we have a local dirty record for this entity,
                        # keep it — the next push will re-push local changes.
                        # L1 MVP: the remote change wins (LWW), but we keep
                        # the dirty record so local changes get another push attempt.
                        pass

            if new_cursor > current_cursor:
                current_cursor = new_cursor

            if not has_more or not changes:
                break

        return current_cursor, total_pulled, errors

    # ── Internal helpers ──────────────────────────────────────────

    def _require_cloud_user(self) -> str:
        """Return the cloud user ID or raise if not logged in."""
        uid = self._auth_svc.get_cloud_user_id()
        if not uid:
            raise CloudSyncError(
                "未登录云账户，请先在个人账户中登录。",
                error_kind="not_logged_in",
                suggestion="请在应用设置的「个人账户」页面登录云账户。",
            )
        return uid

    def _get_sync_state(
        self, project_id: str, cloud_user_id: str
    ) -> CloudSyncState | None:
        """Fetch the sync state for a project and user."""
        return (
            self._db.query(CloudSyncState)
            .filter(
                CloudSyncState.project_id == project_id,
                CloudSyncState.cloud_user_id == cloud_user_id,
                CloudSyncState.deleted_at.is_(None),
            )
            .first()
        )
