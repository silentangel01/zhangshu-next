"""Tests for FTS5 full-text search infrastructure."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
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

from app.infrastructure.search_fts import (  # noqa: E402
    FTS_TABLE,
    detect_fts5_support,
    ensure_search_fts_schema,
)
from app.models.character import Character  # noqa: E402
from app.models.clue import Clue  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.setting_item import SettingItem  # noqa: E402
from app.repositories.search_index_repo import SearchIndexRepository  # noqa: E402


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    ensure_search_fts_schema(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


def _make_project(session):
    pid = str(uuid4())
    project = Project(id=pid, title="搜索测试项目")
    session.add(project)
    session.commit()
    return pid


def _make_chapter(session, project_id, title, content):
    cid = str(uuid4())
    chapter = Chapter(
        id=cid, project_id=project_id, title=title, content=content,
        word_count=len(content), order_index=0,
    )
    session.add(chapter)
    session.commit()
    return cid


def _make_character(session, project_id, name, summary):
    char_id = str(uuid4())
    char = Character(
        id=char_id, project_id=project_id, name=name, summary=summary,
    )
    session.add(char)
    session.commit()
    return char_id


def _make_setting(session, project_id, title, summary, detail):
    sid = str(uuid4())
    setting = SettingItem(
        id=sid, project_id=project_id, title=title, item_type="world",
        summary=summary, detail=detail,
    )
    session.add(setting)
    session.commit()
    return sid


# -- capability detection


def test_detect_fts5_support(db_engine):
    with db_engine.connect() as conn:
        caps = detect_fts5_support(conn)
    assert caps.supports_fts5 is True
    assert caps.supports_trigram is True
    assert caps.tokenizer == "trigram"


# -- backfill


def test_backfill_indexes_existing_data(db_session):
    pid = _make_project(db_session)
    _make_chapter(db_session, pid, "第一章", "这是第一章的内容")
    _make_character(db_session, pid, "主角", "一个勇敢的人")

    # Rebuild should pick up existing data
    repo = SearchIndexRepository(db_session)
    count = repo.rebuild_project(pid)
    assert count >= 2


# -- search


def test_search_chapter_by_content(db_session):
    pid = _make_project(db_session)
    _make_chapter(db_session, pid, "测试章节", "今天天气很好适合写作")

    repo = SearchIndexRepository(db_session)
    rows, total = repo.search(pid, "天气很好")
    assert total >= 1
    assert any(r.entity_type == "chapter" for r in rows)


def test_search_character_by_name(db_session):
    pid = _make_project(db_session)
    _make_character(db_session, pid, "李逍遥", "一个剑客")

    repo = SearchIndexRepository(db_session)
    rows, total = repo.search(pid, "李逍遥")
    assert total >= 1
    assert any(r.entity_type == "character" for r in rows)


def test_search_setting_by_detail(db_session):
    pid = _make_project(db_session)
    _make_setting(db_session, pid, "武林门派", "各大门派", "少林派是天下武功之宗")

    repo = SearchIndexRepository(db_session)
    rows, total = repo.search(pid, "少林派")
    assert total >= 1
    assert any(r.entity_type == "setting" for r in rows)


def test_search_type_filter(db_session):
    pid = _make_project(db_session)
    _make_chapter(db_session, pid, "武林大会", "各大门派齐聚一堂")
    _make_character(db_session, pid, "武林盟主", "统领江湖")

    repo = SearchIndexRepository(db_session)

    # Filter to chapters only
    rows, total = repo.search(pid, "武林", entity_types=["chapter"])
    assert all(r.entity_type == "chapter" for r in rows)

    # Filter to characters only
    rows, total = repo.search(pid, "武林", entity_types=["character"])
    assert all(r.entity_type == "character" for r in rows)


def test_search_empty_query(db_session):
    pid = _make_project(db_session)
    repo = SearchIndexRepository(db_session)
    rows, total = repo.search(pid, "")
    assert total == 0
    assert rows == []


def test_search_short_query_uses_like_fallback(db_session):
    pid = _make_project(db_session)
    _make_chapter(db_session, pid, "剑客", "一个剑客的故事")

    repo = SearchIndexRepository(db_session)
    # Single character should use LIKE fallback
    rows, total = repo.search(pid, "剑")
    assert total >= 1


def test_search_after_soft_delete(db_session):
    from datetime import datetime, timezone

    pid = _make_project(db_session)
    cid = _make_chapter(db_session, pid, "已删除章节", "这个章节会被删除")

    # Verify it's searchable
    repo = SearchIndexRepository(db_session)
    rows, _ = repo.search(pid, "已删除章节")
    assert len(rows) >= 1

    # Soft delete
    chapter = db_session.get(Chapter, cid)
    chapter.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    # Should no longer appear
    rows, total = repo.search(pid, "已删除章节")
    assert total == 0


def test_rebuild_project(db_session):
    pid = _make_project(db_session)
    _make_chapter(db_session, pid, "重建测试", "重建索引的测试内容")

    repo = SearchIndexRepository(db_session)
    count = repo.rebuild_project(pid)
    assert count >= 1

    # Search should still work after rebuild
    rows, total = repo.search(pid, "重建索引")
    assert total >= 1


def test_delete_project(db_session):
    pid = _make_project(db_session)
    _make_chapter(db_session, pid, "删除项目测试", "测试删除项目索引")

    repo = SearchIndexRepository(db_session)
    repo.rebuild_project(pid)

    repo.delete_project(pid)

    rows, total = repo.search(pid, "删除项目测试")
    assert total == 0
