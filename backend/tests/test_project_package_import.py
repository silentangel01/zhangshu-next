"""Tests for project package import service."""

import json
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.volume import Volume  # noqa: E402
from app.models.chapter import Chapter  # noqa: E402
from app.models.character import Character  # noqa: E402
from app.models.setting_item import SettingItem  # noqa: E402
from app.services.backup_service import BackupInvalidError, BackupService  # noqa: E402
from app.services.project_package_import_service import (  # noqa: E402
    ProjectPackageImportService,
    ProjectPackagePreviewNotFoundError,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_project_with_backup(db_session):
    project_id = str(uuid4())
    volume_id = str(uuid4())
    chapter_id = str(uuid4())
    character_id = str(uuid4())
    setting_id = str(uuid4())

    now = datetime.now(timezone.utc)
    project = Project(id=project_id, title="测试项目", created_at=now, updated_at=now)
    db_session.add(project)

    volume = Volume(id=volume_id, project_id=project_id, title="第一卷", order_index=0, created_at=now)
    db_session.add(volume)

    chapter = Chapter(
        id=chapter_id, project_id=project_id, volume_id=volume_id,
        title="第一章", content="正文内容", order_index=0,
        status="draft", word_count=4, created_at=now, updated_at=now,
    )
    db_session.add(chapter)

    character = Character(
        id=character_id, project_id=project_id, name="主角",
        role="protagonist", importance="major", status="active",
        summary="", biography="", appearance="", personality="",
        background="", ability="", motivation="", secret="", arc="", notes="",
        created_at=now, updated_at=now,
    )
    db_session.add(character)

    setting = SettingItem(
        id=setting_id, project_id=project_id, title="世界设定",
        item_type="world", canon_status="canon", summary="", detail="",
        tags="", order_index=0, importance="major", node_kind="leaf",
        is_system=False, created_at=now, updated_at=now,
    )
    db_session.add(setting)

    db_session.commit()
    return project_id


def _create_backup_zip(db_session, project_id):
    backup_service = BackupService(db_session)
    backup_file = backup_service.export_project_backup(project_id)
    return backup_file.content.getvalue()


class TestProjectPackageImport:
    def test_preview_package(self, db_session):
        project_id = _make_project_with_backup(db_session)
        backup_bytes = _create_backup_zip(db_session, project_id)

        service = ProjectPackageImportService(db_session)
        preview = service.preview_package(backup_bytes)

        assert preview.preview_id
        assert preview.project_title == "测试项目"
        assert preview.entity_counts.volumes == 1
        assert preview.entity_counts.chapters == 1
        assert preview.entity_counts.characters == 1
        assert preview.entity_counts.settings == 1

    def test_preview_invalid_zip(self, db_session):
        service = ProjectPackageImportService(db_session)
        with pytest.raises(BackupInvalidError):
            service.preview_package(b"not a zip file")

    def test_confirm_package(self, db_session):
        project_id = _make_project_with_backup(db_session)
        backup_bytes = _create_backup_zip(db_session, project_id)

        service = ProjectPackageImportService(db_session)
        preview = service.preview_package(backup_bytes)
        result = service.confirm_package(preview.preview_id)

        assert result.project_id
        assert result.project_id != project_id
        assert "备份恢复" in result.project_title
        assert result.entity_counts.volumes == 1
        assert result.entity_counts.chapters == 1

    def test_confirm_missing_preview(self, db_session):
        service = ProjectPackageImportService(db_session)
        with pytest.raises(ProjectPackagePreviewNotFoundError):
            service.confirm_package("nonexistent-id")

    def test_backup_inspect_readonly(self, db_session):
        project_id = _make_project_with_backup(db_session)
        backup_bytes = _create_backup_zip(db_session, project_id)

        backup_service = BackupService(db_session)
        initial_count = db_session.query(Project).count()

        backup_service.inspect_project_backup(backup_bytes)

        assert db_session.query(Project).count() == initial_count
