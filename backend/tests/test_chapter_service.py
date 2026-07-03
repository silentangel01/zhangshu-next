"""Tests for chapter service version source mapping and throttling."""

import sys
from datetime import datetime, timedelta, timezone
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
from app.schemas.chapter import ChapterUpdate  # noqa: E402
from app.services.chapter_service import ChapterService  # noqa: E402


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


# -- source mapping


def test_manual_save_creates_manual_save_source(db_session):
    pid = _make_project(db_session)
    vid = _make_volume(db_session, pid)
    cid = _make_chapter(db_session, pid, vid, content="原始内容")

    svc = ChapterService(db_session)
    svc.update_chapter(cid, ChapterUpdate(content="新的手动保存内容", save_source="manual"))

    versions = db_session.query(ChapterVersion).filter_by(chapter_id=cid).all()
    assert len(versions) >= 1
    latest = max(versions, key=lambda v: v.created_at)
    assert latest.source == "manual_save"
    assert latest.content == "新的手动保存内容"


def test_autosave_creates_autosave_source(db_session):
    pid = _make_project(db_session)
    vid = _make_volume(db_session, pid)
    cid = _make_chapter(db_session, pid, vid, content="原始内容")

    svc = ChapterService(db_session)
    svc.update_chapter(cid, ChapterUpdate(content="自动保存的内容变化超过两百字" + "补" * 200, save_source="autosave"))

    versions = db_session.query(ChapterVersion).filter_by(chapter_id=cid).all()
    assert len(versions) >= 1
    latest = max(versions, key=lambda v: v.created_at)
    assert latest.source == "autosave"


# -- throttling


def test_manual_save_throttled_when_content_unchanged(db_session):
    pid = _make_project(db_session)
    vid = _make_volume(db_session, pid)
    cid = _make_chapter(db_session, pid, vid, content="不变的内容")

    svc = ChapterService(db_session)
    # First save with content change
    svc.update_chapter(cid, ChapterUpdate(content="变化后的内容", save_source="manual"))
    count_after_first = db_session.query(ChapterVersion).filter_by(chapter_id=cid).count()

    # Second save with no content change — should not create a version
    svc.update_chapter(cid, ChapterUpdate(content="变化后的内容", save_source="manual"))
    count_after_second = db_session.query(ChapterVersion).filter_by(chapter_id=cid).count()

    assert count_after_second == count_after_first


def test_normalize_source_maps_manual_to_manual_save():
    from app.services.chapter_service import ChapterService
    assert ChapterService._normalize_content_version_source("manual") == "manual_save"
    assert ChapterService._normalize_content_version_source("autosave") == "autosave"
    assert ChapterService._normalize_content_version_source("unknown") == "manual_save"
