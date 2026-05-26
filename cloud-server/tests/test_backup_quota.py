"""Tests for backup quota, rate limiting, and stale upload cleanup."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.cloud_backup import CloudBackup
from app.models.cloud_project import CloudProject
from app.models.user import User, utc_now
from app.services.backup_service import BackupError, BackupService


@pytest.fixture
def quota_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_oss_storage():
    oss = MagicMock()
    oss.is_configured = True
    oss.build_object_key.return_value = "backups/u/p/b/f.zip"
    oss.generate_put_url.return_value = "https://oss.example.com/put"
    return oss


def _seed_user(db, user_id: str) -> User:
    user = User(
        id=user_id,
        email="quota@example.com",
        password_hash="hash",
        display_name="Quota Test",
    )
    db.add(user)
    db.commit()
    return user


def _seed_project(db, project_id: str, owner_id: str) -> CloudProject:
    proj = CloudProject(id=project_id, owner_id=owner_id, title="Test")
    db.add(proj)
    db.commit()
    return proj


def _seed_backup(
    db, backup_id: str, project_id: str, size_bytes: int = 100, status: str = "success"
) -> CloudBackup:
    backup = CloudBackup(
        id=backup_id,
        project_id=project_id,
        object_key=f"backups/{backup_id}",
        filename="f.zip",
        size_bytes=size_bytes,
        status=status,
        upload_id=str(uuid4()),
        upload_expires_at=utc_now() + timedelta(hours=1),
    )
    db.add(backup)
    db.commit()
    return backup


class TestStorageQuota:
    def test_within_quota(self, quota_db, mock_oss_storage):
        user_id = str(uuid4())
        project_id = str(uuid4())
        _seed_user(quota_db, user_id)
        _seed_project(quota_db, project_id, user_id)

        svc = BackupService(quota_db, oss=mock_oss_storage)
        with patch.object(svc._settings, "default_storage_quota_bytes", 10_000):
            # Should not raise
            svc._check_storage_quota(user_id, 100)

    def test_exceeds_quota(self, quota_db, mock_oss_storage):
        user_id = str(uuid4())
        project_id = str(uuid4())
        _seed_user(quota_db, user_id)
        _seed_project(quota_db, project_id, user_id)
        _seed_backup(quota_db, str(uuid4()), project_id, size_bytes=900)

        svc = BackupService(quota_db, oss=mock_oss_storage)
        with patch.object(svc._settings, "default_storage_quota_bytes", 1_000):
            with pytest.raises(BackupError, match="空间已达上限"):
                svc._check_storage_quota(user_id, 200)


class TestCountQuota:
    def test_within_count(self, quota_db, mock_oss_storage):
        user_id = str(uuid4())
        project_id = str(uuid4())
        _seed_user(quota_db, user_id)
        _seed_project(quota_db, project_id, user_id)

        svc = BackupService(quota_db, oss=mock_oss_storage)
        with patch.object(svc._settings, "default_backup_count_quota", 10):
            svc._check_count_quota(user_id)

    def test_exceeds_count(self, quota_db, mock_oss_storage):
        user_id = str(uuid4())
        project_id = str(uuid4())
        _seed_user(quota_db, user_id)
        _seed_project(quota_db, project_id, user_id)
        for _ in range(5):
            _seed_backup(quota_db, str(uuid4()), project_id)

        svc = BackupService(quota_db, oss=mock_oss_storage)
        with patch.object(svc._settings, "default_backup_count_quota", 5):
            with pytest.raises(BackupError, match="数量已达上限"):
                svc._check_count_quota(user_id)


class TestRateLimit:
    def test_within_rate(self, quota_db, mock_oss_storage):
        user_id = str(uuid4())
        project_id = str(uuid4())
        _seed_user(quota_db, user_id)
        _seed_project(quota_db, project_id, user_id)

        svc = BackupService(quota_db, oss=mock_oss_storage)
        with patch.object(svc._settings, "rate_limit_backup_init_per_hour", 10):
            svc._check_rate_limit(user_id)

    def test_exceeds_rate(self, quota_db, mock_oss_storage):
        user_id = str(uuid4())
        project_id = str(uuid4())
        _seed_user(quota_db, user_id)
        _seed_project(quota_db, project_id, user_id)
        for _ in range(5):
            _seed_backup(quota_db, str(uuid4()), project_id, status="uploading")

        svc = BackupService(quota_db, oss=mock_oss_storage)
        with patch.object(svc._settings, "rate_limit_backup_init_per_hour", 5):
            with pytest.raises(BackupError, match="频率过高"):
                svc._check_rate_limit(user_id)


class TestStaleUploadCleanup:
    def test_cleanup_marks_stale(self, quota_db, mock_oss_storage):
        project_id = str(uuid4())
        user_id = str(uuid4())
        _seed_user(quota_db, user_id)
        _seed_project(quota_db, project_id, user_id)

        # Create a stale uploading record
        backup = CloudBackup(
            id=str(uuid4()),
            project_id=project_id,
            object_key="backups/stale",
            filename="stale.zip",
            size_bytes=100,
            status="uploading",
            upload_id=str(uuid4()),
            upload_expires_at=utc_now() - timedelta(hours=12),
            created_at=utc_now() - timedelta(hours=12),
        )
        quota_db.add(backup)
        quota_db.commit()

        svc = BackupService(quota_db, oss=mock_oss_storage)
        cleaned = svc.cleanup_stale_uploads()

        assert cleaned == 1
        quota_db.refresh(backup)
        assert backup.status == "failed"

    def test_cleanup_skips_recent(self, quota_db, mock_oss_storage):
        project_id = str(uuid4())
        user_id = str(uuid4())
        _seed_user(quota_db, user_id)
        _seed_project(quota_db, project_id, user_id)

        # Create a recent uploading record
        backup = CloudBackup(
            id=str(uuid4()),
            project_id=project_id,
            object_key="backups/recent",
            filename="recent.zip",
            size_bytes=100,
            status="uploading",
            upload_id=str(uuid4()),
            upload_expires_at=utc_now() + timedelta(hours=1),
        )
        quota_db.add(backup)
        quota_db.commit()

        svc = BackupService(quota_db, oss=mock_oss_storage)
        cleaned = svc.cleanup_stale_uploads()

        assert cleaned == 0
        quota_db.refresh(backup)
        assert backup.status == "uploading"
