"""Tests for the setting tree (folder + page) system."""

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base
from app.models.setting_item import SettingItem
from app.models.project import Project
from app.services.setting_service import (
    SettingFolderNotEmptyError,
    SettingInvalidParentError,
    SettingParentCycleError,
    SettingService,
    SettingSystemFolderProtectedError,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def project_id(db_session):
    pid = str(uuid4())
    project = Project(id=pid, title="Test Project")
    db_session.add(project)
    db_session.commit()
    return pid


@pytest.fixture
def setting_service(db_session):
    return SettingService(db_session)


class TestDefaultFolderCreation:
    def test_list_creates_root_and_default_folders(self, db_session, project_id, setting_service):
        items = setting_service.list_project_settings(project_id)
        folders = [i for i in items if i.node_kind == "folder"]
        folder_keys = {f.folder_key for f in folders}
        assert "root" in folder_keys
        assert "characters" in folder_keys
        assert "power" in folder_keys
        assert "world" in folder_keys
        assert "history" in folder_keys

    def test_idempotent_creation(self, db_session, project_id, setting_service):
        setting_service.list_project_settings(project_id)
        setting_service.list_project_settings(project_id)
        items = setting_service.list_project_settings(project_id)
        folders = [i for i in items if i.node_kind == "folder"]
        assert len(folders) == 5  # root + 4 defaults

    def test_system_folders_are_protected(self, db_session, project_id, setting_service):
        items = setting_service.list_project_settings(project_id)
        for item in items:
            if item.is_system:
                with pytest.raises(SettingSystemFolderProtectedError):
                    setting_service.delete_setting(item.id)


class TestPageCreation:
    def test_create_page_without_parent_fails(self, db_session, project_id, setting_service):
        from app.schemas.setting import SettingCreate

        setting_service.list_project_settings(project_id)
        with pytest.raises(SettingInvalidParentError):
            setting_service.create_setting(
                project_id,
                SettingCreate(title="Orphan Page", node_kind="page", parent_id=None),
            )

    def test_create_page_inherits_type_from_folder(self, db_session, project_id, setting_service):
        from app.schemas.setting import SettingCreate

        setting_service.list_project_settings(project_id)
        chars_folder = setting_service.setting_repo.get_active_by_project_and_folder_key(
            project_id, "characters"
        )
        page = setting_service.create_setting(
            project_id,
            SettingCreate(
                title="Zhang San",
                node_kind="page",
                parent_id=chars_folder.id,
            ),
        )
        assert page.item_type == "character"
        assert page.node_kind == "page"

    def test_create_page_with_explicit_type(self, db_session, project_id, setting_service):
        from app.schemas.setting import SettingCreate

        setting_service.list_project_settings(project_id)
        world_folder = setting_service.setting_repo.get_active_by_project_and_folder_key(
            project_id, "world"
        )
        page = setting_service.create_setting(
            project_id,
            SettingCreate(
                title="Custom World",
                node_kind="page",
                parent_id=world_folder.id,
                item_type="location",
            ),
        )
        assert page.item_type == "location"


class TestFolderCreation:
    def test_create_user_folder(self, db_session, project_id, setting_service):
        from app.schemas.setting import SettingCreate

        setting_service.list_project_settings(project_id)
        folder = setting_service.create_setting(
            project_id,
            SettingCreate(
                title="My Folder",
                node_kind="folder",
                folder_default_item_type="custom",
            ),
        )
        assert folder.node_kind == "folder"
        assert folder.is_system is False
        assert folder.folder_key is None

    def test_create_folder_under_page_fails(self, db_session, project_id, setting_service):
        from app.schemas.setting import SettingCreate

        setting_service.list_project_settings(project_id)
        chars_folder = setting_service.setting_repo.get_active_by_project_and_folder_key(
            project_id, "characters"
        )
        page = setting_service.create_setting(
            project_id,
            SettingCreate(
                title="A Page",
                node_kind="page",
                parent_id=chars_folder.id,
            ),
        )
        with pytest.raises(SettingInvalidParentError):
            setting_service.create_setting(
                project_id,
                SettingCreate(
                    title="Sub Folder",
                    node_kind="folder",
                    parent_id=page.id,
                ),
            )


class TestCycleDetection:
    def test_self_parent_cycle(self, db_session, project_id, setting_service):
        from app.schemas.setting import SettingCreate, SettingUpdate

        setting_service.list_project_settings(project_id)
        folder = setting_service.create_setting(
            project_id,
            SettingCreate(title="Folder A", node_kind="folder"),
        )
        with pytest.raises(SettingParentCycleError):
            setting_service.update_setting(
                folder.id, SettingUpdate(parent_id=folder.id)
            )


class TestNodeKindFilter:
    def test_filter_pages_only(self, db_session, project_id, setting_service):
        from app.schemas.setting import SettingCreate

        setting_service.list_project_settings(project_id)
        chars_folder = setting_service.setting_repo.get_active_by_project_and_folder_key(
            project_id, "characters"
        )
        setting_service.create_setting(
            project_id,
            SettingCreate(
                title="Li Si",
                node_kind="page",
                parent_id=chars_folder.id,
            ),
        )
        pages = setting_service.list_project_settings(project_id, node_kind="page")
        for p in pages:
            assert p.node_kind == "page"

    def test_filter_folders_only(self, db_session, project_id, setting_service):
        setting_service.list_project_settings(project_id)
        folders = setting_service.list_project_settings(project_id, node_kind="folder")
        for f in folders:
            assert f.node_kind == "folder"


class TestFolderDeletion:
    def test_delete_non_empty_folder_fails(self, db_session, project_id, setting_service):
        from app.schemas.setting import SettingCreate

        setting_service.list_project_settings(project_id)
        folder = setting_service.create_setting(
            project_id,
            SettingCreate(title="Parent Folder", node_kind="folder"),
        )
        setting_service.create_setting(
            project_id,
            SettingCreate(
                title="Child Page",
                node_kind="page",
                parent_id=folder.id,
            ),
        )
        with pytest.raises(SettingFolderNotEmptyError):
            setting_service.delete_setting(folder.id)

    def test_delete_empty_user_folder(self, db_session, project_id, setting_service):
        from app.schemas.setting import SettingCreate

        setting_service.list_project_settings(project_id)
        folder = setting_service.create_setting(
            project_id,
            SettingCreate(title="Empty Folder", node_kind="folder"),
        )
        result = setting_service.delete_setting(folder.id)
        assert result.deleted_at is not None
