"""Regression tests for cloud import fallback to backup restore.

Tests that ``CloudSyncService.import_cloud_project()`` correctly falls back
to downloading the latest cloud backup when incremental sync data is empty,
and that it handles both the remote API shape (``id``) and the legacy shape
(``cloud_backup_id``) for backup items.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.cloud_project_link import CloudProjectLink  # noqa: E402
from app.models.cloud_sync_state import CloudSyncState  # noqa: E402
from app.services.cloud_sync_service import (  # noqa: E402
    CloudSyncError,
    CloudSyncService,
    _normalize_remote_backup_item,
)


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def restore_report():
    """A fake RestoreReport returned by the mocked BackupService."""
    return SimpleNamespace(
        project_id=str(uuid4()),
        project_title="从备份恢复的项目",
        counts=SimpleNamespace(volumes=2, chapters=5, materials=3),
        warnings=[],
        errors=[],
    )


@pytest.fixture
def mock_httpx():
    """Patch httpx.Client so the GET returns fake backup bytes."""
    fake_response = MagicMock()
    fake_response.content = b"FAKE_BACKUP_ZIP_BYTES"
    fake_response.raise_for_status = MagicMock()

    fake_client = MagicMock()
    fake_client.__enter__ = MagicMock(return_value=fake_client)
    fake_client.__exit__ = MagicMock(return_value=False)
    fake_client.get.return_value = fake_response

    with patch("httpx.Client", return_value=fake_client) as mock_cls:
        yield mock_cls, fake_client


# ── Helper: build a service with mocked auth ──────────────────────


def _make_service(db_session, mock_client):
    """Create a CloudSyncService whose ``call_with_refresh`` invokes the
    passed callable with *mock_client* (so each API call goes to the mock).
    """
    svc = CloudSyncService(db_session)

    def _fake_call_with_refresh(fn):
        return fn(mock_client)

    svc._auth_svc.call_with_refresh = _fake_call_with_refresh
    return svc


# ── Unit tests for _normalize_remote_backup_item ─────────────────


class TestNormalizeRemoteBackupItem:
    def test_remote_api_shape_with_id(self):
        item = {
            "id": "backup-remote-1",
            "filename": "test.zip",
            "status": "success",
            "created_at": "2026-05-30T10:00:00",
            "uploaded_at": "2026-05-30T10:01:00",
        }
        result = _normalize_remote_backup_item(item)
        assert result is not None
        assert result["id"] == "backup-remote-1"
        assert result["status"] == "success"
        assert result["uploaded_at"] == "2026-05-30T10:01:00"

    def test_legacy_shape_with_cloud_backup_id(self):
        item = {
            "cloud_backup_id": "backup-legacy-1",
            "status": "success",
            "created_at": "2026-05-30T09:00:00",
        }
        result = _normalize_remote_backup_item(item)
        assert result is not None
        assert result["id"] == "backup-legacy-1"

    def test_id_takes_precedence_over_cloud_backup_id(self):
        item = {
            "id": "preferred-id",
            "cloud_backup_id": "fallback-id",
            "status": "success",
            "created_at": "",
        }
        result = _normalize_remote_backup_item(item)
        assert result is not None
        assert result["id"] == "preferred-id"

    def test_non_success_status_returns_none(self):
        assert _normalize_remote_backup_item({"id": "x", "status": "uploading"}) is None
        assert _normalize_remote_backup_item({"id": "x", "status": "failed"}) is None
        assert _normalize_remote_backup_item({"id": "x", "status": ""}) is None

    def test_missing_id_returns_none(self):
        assert _normalize_remote_backup_item({"status": "success"}) is None
        assert _normalize_remote_backup_item({"status": "success", "id": ""}) is None
        assert _normalize_remote_backup_item({"status": "success", "id": None}) is None

    def test_empty_dict_returns_none(self):
        assert _normalize_remote_backup_item({}) is None


# ── Integration tests: import_cloud_project → backup fallback ─────


class TestImportFromBackupRemoteShape:
    """Test that the backup fallback works with the remote API response shape."""

    def test_import_from_backup_remote_api_shape(
        self, db_session, restore_report, mock_httpx
    ):
        """Remote backup list uses ``id`` field (not ``cloud_backup_id``)."""
        mock_client = MagicMock()

        # sync_pull returns empty → triggers backup fallback
        mock_client.sync_pull.return_value = {
            "changes": [],
            "new_cursor": 0,
            "has_more": False,
        }

        # list_backups returns remote API shape with ``id``
        mock_client.list_backups.return_value = {
            "items": [
                {
                    "id": "backup-remote-1",
                    "filename": "test.zip",
                    "size_bytes": 1024,
                    "checksum_sha256": "abc123",
                    "status": "success",
                    "created_at": "2026-05-30T10:00:00",
                    "uploaded_at": "2026-05-30T10:01:00",
                },
            ],
            "total": 1,
        }

        mock_client.get_backup_download_url.return_value = {
            "download_url": "https://example.test/backup.zip",
        }

        with patch.object(
            CloudSyncService, "_require_cloud_user", return_value="user-123"
        ):
            svc = _make_service(db_session, mock_client)

            with patch(
                "app.services.backup_service.BackupService.restore_project_backup",
                return_value=restore_report,
            ):
                result = svc.import_cloud_project("cloud-proj-test")

        # Verify the import succeeded
        assert result["local_project_id"] == restore_report.project_id
        assert result["title"] == "从备份恢复的项目"
        assert result["volumes_count"] == 2
        assert result["chapters_count"] == 5
        assert result["mode"] == "restored_as_new"

        # Verify download URL was called with the remote ``id``
        mock_client.get_backup_download_url.assert_called_once_with(
            "cloud-proj-test", "backup-remote-1"
        )

        # Verify CloudProjectLink and CloudSyncState were created
        link = db_session.query(CloudProjectLink).filter(
            CloudProjectLink.cloud_project_id == "cloud-proj-test"
        ).first()
        assert link is not None
        assert link.project_id == restore_report.project_id

        sync_state = db_session.query(CloudSyncState).filter(
            CloudSyncState.project_id == restore_report.project_id
        ).first()
        assert sync_state is not None
        assert sync_state.last_cursor == 0  # backup restore, not sync

    def test_import_from_backup_legacy_cloud_backup_id(
        self, db_session, restore_report, mock_httpx
    ):
        """Legacy items with ``cloud_backup_id`` should still work."""
        mock_client = MagicMock()
        mock_client.sync_pull.return_value = {
            "changes": [], "new_cursor": 0, "has_more": False,
        }
        mock_client.list_backups.return_value = {
            "items": [
                {
                    "cloud_backup_id": "backup-legacy-1",
                    "status": "success",
                    "created_at": "2026-05-30T09:00:00",
                },
            ],
        }
        mock_client.get_backup_download_url.return_value = {
            "download_url": "https://example.test/backup.zip",
        }

        with patch.object(
            CloudSyncService, "_require_cloud_user", return_value="user-123"
        ):
            svc = _make_service(db_session, mock_client)
            with patch(
                "app.services.backup_service.BackupService.restore_project_backup",
                return_value=restore_report,
            ):
                result = svc.import_cloud_project("cloud-proj-legacy")

        assert result["local_project_id"] == restore_report.project_id
        mock_client.get_backup_download_url.assert_called_once_with(
            "cloud-proj-legacy", "backup-legacy-1"
        )

    def test_import_from_backup_picks_latest_by_uploaded_at(
        self, db_session, restore_report, mock_httpx
    ):
        """When multiple backups exist, the one with the latest uploaded_at wins."""
        mock_client = MagicMock()
        mock_client.sync_pull.return_value = {
            "changes": [], "new_cursor": 0, "has_more": False,
        }
        mock_client.list_backups.return_value = {
            "items": [
                {
                    "id": "backup-old",
                    "status": "success",
                    "created_at": "2026-05-29T10:00:00",
                    "uploaded_at": "2026-05-29T10:01:00",
                },
                {
                    "id": "backup-new",
                    "status": "success",
                    "created_at": "2026-05-30T10:00:00",
                    "uploaded_at": "2026-05-30T10:01:00",
                },
            ],
            "total": 2,
        }
        mock_client.get_backup_download_url.return_value = {
            "download_url": "https://example.test/backup.zip",
        }

        with patch.object(
            CloudSyncService, "_require_cloud_user", return_value="user-123"
        ):
            svc = _make_service(db_session, mock_client)
            with patch(
                "app.services.backup_service.BackupService.restore_project_backup",
                return_value=restore_report,
            ):
                svc.import_cloud_project("cloud-proj-multi")

        mock_client.get_backup_download_url.assert_called_once_with(
            "cloud-proj-multi", "backup-new"
        )


class TestImportFromBackupEmptyProject:
    """Verify that real empty projects still raise ``empty_project``."""

    def test_empty_project_all_uploading(self, db_session):
        """All backups still uploading → empty_project."""
        mock_client = MagicMock()
        mock_client.sync_pull.return_value = {
            "changes": [], "new_cursor": 0, "has_more": False,
        }
        mock_client.list_backups.return_value = {
            "items": [
                {"id": "b1", "status": "uploading", "created_at": "2026-05-30T10:00:00"},
                {"id": "b2", "status": "uploading", "created_at": "2026-05-30T11:00:00"},
            ],
            "total": 2,
        }

        with patch.object(
            CloudSyncService, "_require_cloud_user", return_value="user-123"
        ):
            svc = _make_service(db_session, mock_client)

            with pytest.raises(CloudSyncError) as exc_info:
                svc.import_cloud_project("cloud-proj-empty")

        assert exc_info.value.error_kind == "empty_project"

    def test_empty_project_all_failed(self, db_session):
        """All backups failed → empty_project."""
        mock_client = MagicMock()
        mock_client.sync_pull.return_value = {
            "changes": [], "new_cursor": 0, "has_more": False,
        }
        mock_client.list_backups.return_value = {
            "items": [
                {"id": "b1", "status": "failed", "created_at": "2026-05-30T10:00:00"},
            ],
        }

        with patch.object(
            CloudSyncService, "_require_cloud_user", return_value="user-123"
        ):
            svc = _make_service(db_session, mock_client)

            with pytest.raises(CloudSyncError) as exc_info:
                svc.import_cloud_project("cloud-proj-failed")

        assert exc_info.value.error_kind == "empty_project"

    def test_empty_project_no_items(self, db_session):
        """Empty items list → empty_project."""
        mock_client = MagicMock()
        mock_client.sync_pull.return_value = {
            "changes": [], "new_cursor": 0, "has_more": False,
        }
        mock_client.list_backups.return_value = {"items": [], "total": 0}

        with patch.object(
            CloudSyncService, "_require_cloud_user", return_value="user-123"
        ):
            svc = _make_service(db_session, mock_client)

            with pytest.raises(CloudSyncError) as exc_info:
                svc.import_cloud_project("cloud-proj-none")

        assert exc_info.value.error_kind == "empty_project"

    def test_empty_project_missing_id(self, db_session):
        """Items with success status but no id → empty_project."""
        mock_client = MagicMock()
        mock_client.sync_pull.return_value = {
            "changes": [], "new_cursor": 0, "has_more": False,
        }
        mock_client.list_backups.return_value = {
            "items": [
                {"status": "success", "created_at": "2026-05-30T10:00:00"},
            ],
        }

        with patch.object(
            CloudSyncService, "_require_cloud_user", return_value="user-123"
        ):
            svc = _make_service(db_session, mock_client)

            with pytest.raises(CloudSyncError) as exc_info:
                svc.import_cloud_project("cloud-proj-noid")

        assert exc_info.value.error_kind == "empty_project"


class TestImportPrefersIncrementalSync:
    """When incremental sync data exists, it should be used instead of backup."""

    def test_sync_data_takes_priority(self, db_session):
        """If sync_pull returns changes, backup path is never called."""
        proj_id = str(uuid4())
        mock_client = MagicMock()
        mock_client.sync_pull.return_value = {
            "changes": [
                {
                    "entity_type": "projects",
                    "entity_id": proj_id,
                    "action": "upsert",
                    "data": {
                        "id": proj_id,
                        "title": "增量导入项目",
                        "author": None,
                        "genre": None,
                        "summary": None,
                        "tags": "[]",
                        "cover_image_path": None,
                        "status": "planning",
                        "target_word_count": None,
                        "created_at": "2026-05-30T10:00:00+00:00",
                        "updated_at": "2026-05-30T10:00:00+00:00",
                        "deleted_at": None,
                        "version": 1,
                    },
                },
            ],
            "new_cursor": 1,
            "has_more": False,
        }

        with patch.object(
            CloudSyncService, "_require_cloud_user", return_value="user-123"
        ):
            svc = _make_service(db_session, mock_client)
            result = svc.import_cloud_project("cloud-proj-sync")

        assert result["local_project_id"] == proj_id
        assert result["title"] == "增量导入项目"

        # list_backups should NOT have been called
        mock_client.list_backups.assert_not_called()
