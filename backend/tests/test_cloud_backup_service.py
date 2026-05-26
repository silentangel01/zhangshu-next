"""Tests for CloudBackupService with mocked CloudApiClient."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.app_config import AppConfig  # noqa: E402
from app.models.cloud_backup_record import CloudBackupRecord  # noqa: E402
from app.models.cloud_project_link import CloudProjectLink  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.services.cloud_auth_service import CloudAuthService  # noqa: E402
from app.services.cloud_backup_service import (  # noqa: E402
    CloudBackupError,
    CloudBackupService,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_project(db_session):
    project_id = str(uuid4())
    project = Project(id=project_id, title="测试项目")
    db_session.add(project)
    db_session.commit()
    return project_id


def _seed_login_tokens(db_session):
    """Seed encrypted tokens so CloudAuthService thinks we are logged in."""
    from app.infrastructure.config_crypto import encrypt_value

    keys = {
        "cloud_access_token": encrypt_value("fake-access-token"),
        "cloud_refresh_token": encrypt_value("fake-refresh-token"),
        "cloud_user_id": encrypt_value("user-123"),
        "cloud_user_email": encrypt_value("test@example.com"),
    }
    for key, value in keys.items():
        db_session.add(
            AppConfig(config_key=key, config_value=value, is_encrypted=True)
        )
    db_session.commit()


# ── enable_cloud ──────────────────────────────────────────────────


@patch("app.services.cloud_backup_service.CloudApiClient")
def test_enable_cloud_creates_link(mock_client_cls, db_session):
    project_id = _make_project(db_session)
    _seed_login_tokens(db_session)

    mock_client = MagicMock()
    mock_client.create_cloud_project.return_value = {"id": "cloud-proj-1"}
    mock_client_cls.return_value = mock_client
    # Also patch the one created inside CloudAuthService.get_api_client
    with patch(
        "app.services.cloud_auth_service.CloudApiClient", return_value=mock_client
    ):
        service = CloudBackupService(db_session)
        link = service.enable_cloud(project_id)

    assert link.cloud_enabled is True
    assert link.cloud_project_id == "cloud-proj-1"
    assert link.provider == "zhangshu"


def test_enable_cloud_not_logged_in(db_session):
    project_id = _make_project(db_session)
    service = CloudBackupService(db_session)
    with pytest.raises(CloudBackupError, match="请先登录"):
        service.enable_cloud(project_id)


# ── get_status ────────────────────────────────────────────────────


def test_get_status_not_enabled(db_session):
    project_id = _make_project(db_session)
    service = CloudBackupService(db_session)
    status = service.get_status(project_id)
    assert status["cloud_enabled"] is False
    assert status["status"] == "inactive"


@patch("app.services.cloud_backup_service.CloudApiClient")
def test_get_status_enabled(mock_client_cls, db_session):
    project_id = _make_project(db_session)
    _seed_login_tokens(db_session)

    mock_client = MagicMock()
    mock_client.create_cloud_project.return_value = {"id": "cloud-proj-2"}
    mock_client_cls.return_value = mock_client

    with patch(
        "app.services.cloud_auth_service.CloudApiClient", return_value=mock_client
    ):
        service = CloudBackupService(db_session)
        service.enable_cloud(project_id)

    status = service.get_status(project_id)
    assert status["cloud_enabled"] is True
    assert status["cloud_project_id"] == "cloud-proj-2"


# ── trigger_backup ────────────────────────────────────────────────


@patch("app.services.cloud_backup_service.CloudApiClient")
def test_trigger_backup_success(mock_client_cls, db_session):
    project_id = _make_project(db_session)
    _seed_login_tokens(db_session)

    mock_client = MagicMock()
    mock_client.create_cloud_project.return_value = {"id": "cloud-proj-3"}
    mock_client.init_backup_upload.return_value = {
        "upload_url": "https://oss.example.com/upload",
        "upload_id": "upload-abc",
    }
    mock_client.complete_backup.return_value = {
        "id": "backup-xyz",
        "object_key": "projects/abc/backup.zip",
    }
    mock_client_cls.return_value = mock_client

    with patch(
        "app.services.cloud_auth_service.CloudApiClient", return_value=mock_client
    ):
        service = CloudBackupService(db_session)
        service.enable_cloud(project_id)

        with patch.object(
            service._backup_svc,
            "build_project_backup_bytes",
            return_value=(b"fake-zip-content", "test_backup.zip"),
        ):
            record = service.trigger_backup(project_id)

    assert record.status == "success"
    assert record.cloud_backup_id == "backup-xyz"
    assert record.filename == "test_backup.zip"
    assert record.size_bytes == len(b"fake-zip-content")
    mock_client.upload_backup.assert_called_once()


def test_trigger_backup_not_enabled(db_session):
    project_id = _make_project(db_session)
    _seed_login_tokens(db_session)
    service = CloudBackupService(db_session)
    with pytest.raises(CloudBackupError, match="请先为该项目启用"):
        service.trigger_backup(project_id)


# ── list_backups ──────────────────────────────────────────────────


@patch("app.services.cloud_backup_service.CloudApiClient")
def test_list_backups(mock_client_cls, db_session):
    project_id = _make_project(db_session)
    _seed_login_tokens(db_session)

    mock_client = MagicMock()
    mock_client.create_cloud_project.return_value = {"id": "cloud-proj-4"}
    mock_client.init_backup_upload.return_value = {
        "upload_url": "https://oss.example.com/upload",
        "upload_id": "upload-def",
    }
    mock_client.complete_backup.return_value = {
        "id": "backup-111",
        "object_key": "key",
    }
    mock_client_cls.return_value = mock_client

    with patch(
        "app.services.cloud_auth_service.CloudApiClient", return_value=mock_client
    ):
        service = CloudBackupService(db_session)
        service.enable_cloud(project_id)

        with patch.object(
            service._backup_svc,
            "build_project_backup_bytes",
            return_value=(b"zip1", "backup1.zip"),
        ):
            service.trigger_backup(project_id)

    records = service.list_backups(project_id)
    assert len(records) == 1
    assert records[0].cloud_backup_id == "backup-111"


# ── CloudApiNotConfiguredError ────────────────────────────────────


def test_account_status_not_configured(db_session):
    with patch.dict("os.environ", {"ZHANGSHU_CLOUD_API_BASE_URL": ""}, clear=False):
        auth_service = CloudAuthService(db_session)
        status = auth_service.get_account_status()
        assert status["logged_in"] is False
        assert status["cloud_available"] is False
