"""Tests for unified version management service."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402

# Import all models to resolve FK references
import app.models.project  # noqa: E402, F401
import app.models.volume  # noqa: E402, F401
import app.models.chapter  # noqa: E402, F401
import app.models.chapter_version  # noqa: E402, F401
import app.models.entity_version  # noqa: E402, F401
import app.models.character  # noqa: E402, F401
import app.models.clue  # noqa: E402, F401
import app.models.setting_item  # noqa: E402, F401
import app.models.outline_item  # noqa: E402, F401
import app.models.knowledge_source  # noqa: E402, F401
import app.models.knowledge_chunk  # noqa: E402, F401
import app.models.timeline_event  # noqa: E402, F401
import app.models.timeline_track  # noqa: E402, F401
import app.models.graph_node  # noqa: E402, F401
import app.models.graph_edge  # noqa: E402, F401

from app.models.chapter import Chapter  # noqa: E402
from app.models.character import Character  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.setting_item import SettingItem  # noqa: E402
from app.schemas.version import (  # noqa: E402
    CreateVersionSnapshotRequest,
    UpdateVersionRequest,
    VersionCompareRequest,
)
from app.services.version_service import (  # noqa: E402
    VersionEntityNotFoundError,
    VersionNotFoundError,
    VersionPinnedError,
    VersionService,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_project(session):
    pid = str(uuid4())
    now = datetime.now(timezone.utc)
    project = Project(id=pid, title="版本测试项目", created_at=now, updated_at=now)
    session.add(project)
    session.commit()
    return pid


def _make_chapter(session, project_id, title="测试章节", content="测试内容"):
    cid = str(uuid4())
    chapter = Chapter(
        id=cid, project_id=project_id, title=title, content=content,
        word_count=len(content), order_index=0,
    )
    session.add(chapter)
    session.commit()
    return cid


def _make_character(session, project_id, name="测试角色"):
    char_id = str(uuid4())
    char = Character(
        id=char_id, project_id=project_id, name=name,
        summary="角色简介", biography="角色传记",
    )
    session.add(char)
    session.commit()
    return char_id


def _make_setting(session, project_id, title="测试设定"):
    sid = str(uuid4())
    setting = SettingItem(
        id=sid, project_id=project_id, title=title,
        item_type="world", summary="设定摘要", detail="设定详情",
    )
    session.add(setting)
    session.commit()
    return sid


# -- list versions


def test_list_versions_empty(db_session):
    pid = _make_project(db_session)
    svc = VersionService(db_session)
    resp = svc.list_versions(pid)
    assert resp.total == 0
    assert resp.versions == []


# -- create snapshot


def test_create_chapter_snapshot(db_session):
    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid)

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="chapter", entity_id=cid, label="初稿",
    ))

    assert item.entity_type == "chapter"
    assert item.entity_id == cid
    assert item.label == "初稿"
    assert item.version_ref.startswith("chapter_version:")


def test_create_character_snapshot(db_session):
    pid = _make_project(db_session)
    char_id = _make_character(db_session, pid)

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="character", entity_id=char_id,
    ))

    assert item.entity_type == "character"
    assert item.entity_id == char_id
    assert item.version_ref.startswith("entity_version:")


def test_create_setting_snapshot(db_session):
    pid = _make_project(db_session)
    sid = _make_setting(db_session, pid)

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="setting", entity_id=sid,
    ))

    assert item.entity_type == "setting"
    assert item.entity_id == sid


def test_create_snapshot_nonexistent_entity(db_session):
    pid = _make_project(db_session)
    svc = VersionService(db_session)

    with pytest.raises(VersionEntityNotFoundError):
        svc.create_snapshot(pid, CreateVersionSnapshotRequest(
            entity_type="chapter", entity_id="nonexistent-id",
        ))


# -- get detail


def test_get_version_detail(db_session):
    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid, title="详情测试", content="详情内容")

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="chapter", entity_id=cid,
    ))

    detail = svc.get_version(pid, item.version_ref)
    assert detail.entity_title == "详情测试"
    assert "详情内容" in detail.content_text


def test_get_version_not_found(db_session):
    pid = _make_project(db_session)
    svc = VersionService(db_session)

    with pytest.raises(VersionNotFoundError):
        svc.get_version(pid, "chapter_version:nonexistent")


# -- compare


def test_compare_with_current(db_session):
    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid, title="对比测试", content="原始内容")

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="chapter", entity_id=cid,
    ))

    # Modify the chapter
    chapter = db_session.get(Chapter, cid)
    chapter.content = "修改后的内容"
    db_session.commit()

    # Compare
    result = svc.compare(pid, VersionCompareRequest(version_ref_a=item.version_ref))
    assert len(result.diff) > 0
    assert any(d.tag in ("delete", "insert", "replace") for d in result.diff)


def test_compare_no_changes(db_session):
    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid, title="无变化", content="内容不变")

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="chapter", entity_id=cid,
    ))

    result = svc.compare(pid, VersionCompareRequest(version_ref_a=item.version_ref))
    assert all(d.tag == "equal" for d in result.diff)


# -- restore


def test_restore_chapter_version(db_session):
    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid, title="恢复测试", content="原始内容")

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="chapter", entity_id=cid,
    ))

    # Modify
    chapter = db_session.get(Chapter, cid)
    chapter.content = "被修改的内容"
    chapter.title = "修改后的标题"
    db_session.commit()

    # Restore
    result = svc.restore(pid, item.version_ref)
    assert result.before_restore_ref.startswith("chapter_version:")

    # Verify restored
    chapter = db_session.get(Chapter, cid)
    assert chapter.content == "原始内容"
    assert chapter.title == "恢复测试"


def test_restore_creates_before_restore_snapshot(db_session):
    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid, content="恢复前快照测试")

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="chapter", entity_id=cid,
    ))

    chapter = db_session.get(Chapter, cid)
    chapter.content = "新内容"
    db_session.commit()

    svc.restore(pid, item.version_ref)

    # Check that before_restore snapshot exists
    resp = svc.list_versions(pid, entity_type="chapter", entity_id=cid, source="before_restore")
    assert resp.total >= 1


def test_restore_entity_version(db_session):
    pid = _make_project(db_session)
    char_id = _make_character(db_session, pid, name="原始名字")

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="character", entity_id=char_id,
    ))

    # Modify
    char = db_session.get(Character, char_id)
    char.name = "修改后的名字"
    char.summary = "修改后的简介"
    db_session.commit()

    # Restore
    svc.restore(pid, item.version_ref)

    char = db_session.get(Character, char_id)
    assert char.name == "原始名字"
    assert char.summary == "角色简介"


# -- update (pin/unpin)


def test_pin_and_unpin_version(db_session):
    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid)

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="chapter", entity_id=cid,
    ))

    # Pin
    updated = svc.update_version(pid, item.version_ref, UpdateVersionRequest(is_pinned=True))
    assert updated.is_pinned is True

    # Unpin
    updated = svc.update_version(pid, item.version_ref, UpdateVersionRequest(is_pinned=False))
    assert updated.is_pinned is False


# -- delete


def test_delete_unpinned_version(db_session):
    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid)

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="chapter", entity_id=cid,
    ))

    svc.delete_version(pid, item.version_ref)

    with pytest.raises(VersionNotFoundError):
        svc.get_version(pid, item.version_ref)


def test_delete_pinned_version_raises(db_session):
    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid)

    svc = VersionService(db_session)
    item = svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="chapter", entity_id=cid,
    ))

    svc.update_version(pid, item.version_ref, UpdateVersionRequest(is_pinned=True))

    with pytest.raises(VersionPinnedError):
        svc.delete_version(pid, item.version_ref)


# -- cleanup


def test_cleanup_old_autosave(db_session):
    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid)

    svc = VersionService(db_session)
    # Create a manual snapshot (should not be cleaned up)
    svc.create_snapshot(pid, CreateVersionSnapshotRequest(
        entity_type="chapter", entity_id=cid,
    ))

    result = svc.cleanup(pid, keep_days=30)
    # No old autosave versions to clean
    assert result.deleted_count == 0
