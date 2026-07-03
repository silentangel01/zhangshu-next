"""Tests for chapter version service source mapping."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402

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
from app.models.chapter_version import ChapterVersion  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.volume import Volume  # noqa: E402
from app.schemas.chapter_version import CreateChapterVersionRequest  # noqa: E402
from app.services.chapter_version_service import ChapterVersionService  # noqa: E402


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
    project = Project(id=pid, title="测试项目", created_at=now, updated_at=now)
    session.add(project)
    session.commit()
    return pid


def _make_volume(session, project_id):
    vid = str(uuid4())
    volume = Volume(id=vid, project_id=project_id, title="测试分卷", order_index=0)
    session.add(volume)
    session.commit()
    return vid


def _make_chapter(session, project_id, volume_id, title="测试章节", content="测试内容"):
    cid = str(uuid4())
    chapter = Chapter(
        id=cid, project_id=project_id, volume_id=volume_id,
        title=title, content=content,
        word_count=len(content.replace(" ", "").replace("\n", "")),
        order_index=0,
    )
    session.add(chapter)
    session.commit()
    return cid


def test_create_snapshot_defaults_to_milestone(db_session):
    pid = _make_project(db_session)
    vid = _make_volume(db_session, pid)
    cid = _make_chapter(db_session, pid, vid)

    svc = ChapterVersionService(db_session)
    version = svc.create_snapshot(
        cid, CreateChapterVersionRequest(note="测试里程碑"),
    )

    assert version.source == "milestone"


def test_create_snapshot_legacy_manual_maps_to_milestone(db_session):
    pid = _make_project(db_session)
    vid = _make_volume(db_session, pid)
    cid = _make_chapter(db_session, pid, vid)

    svc = ChapterVersionService(db_session)
    # Legacy caller sending source="manual"
    version = svc.create_snapshot(
        cid, CreateChapterVersionRequest(source="manual", note="旧调用"),
    )

    assert version.source == "milestone"


def test_create_snapshot_restore_source_preserved(db_session):
    pid = _make_project(db_session)
    vid = _make_volume(db_session, pid)
    cid = _make_chapter(db_session, pid, vid)

    svc = ChapterVersionService(db_session)
    version = svc.create_snapshot(
        cid, CreateChapterVersionRequest(source="restore", note="恢复记录"),
    )

    assert version.source == "restore"


def test_create_snapshot_before_restore_preserved(db_session):
    pid = _make_project(db_session)
    vid = _make_volume(db_session, pid)
    cid = _make_chapter(db_session, pid, vid)

    svc = ChapterVersionService(db_session)
    version = svc.create_snapshot(
        cid, CreateChapterVersionRequest(source="before_restore", note="恢复前"),
    )

    assert version.source == "before_restore"


def test_explicit_milestone_source(db_session):
    pid = _make_project(db_session)
    vid = _make_volume(db_session, pid)
    cid = _make_chapter(db_session, pid, vid)

    svc = ChapterVersionService(db_session)
    version = svc.create_snapshot(
        cid, CreateChapterVersionRequest(source="milestone", note="显式里程碑"),
    )

    assert version.source == "milestone"
    assert version.note == "显式里程碑"
