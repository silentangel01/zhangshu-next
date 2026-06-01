"""Tests for sync_serializer — serialize/deserialize all 24 P0/P1 entities."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

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
from app.models.clue import Clue  # noqa: E402
from app.models.outline_item import OutlineItem  # noqa: E402
from app.models.timeline_track import TimelineTrack  # noqa: E402
from app.models.timeline_event import TimelineEvent  # noqa: E402
from app.models.timeline_edge import TimelineEdge  # noqa: E402
from app.models.graph_node import GraphNode  # noqa: E402
from app.models.graph_edge import GraphEdge  # noqa: E402
from app.services.sync_serializer import (  # noqa: E402
    _EXCLUDE_FIELDS,
    SYNC_APPLY_ORDER,
    SYNC_DELETE_ORDER,
    SYNC_ENTITY_MODELS,
    deserialize_entity,
    get_active_entity,
    get_entity_by_id,
    payload_to_json,
    serialize_entity,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ── Registry checks ────────────────────────────────────────────


def test_sync_entity_models_p0_p1_whitelist():
    """P0/P1 sync covers 24 entity types."""
    expected = {
        # P0
        "projects", "volumes", "chapters",
        "characters", "setting_items", "clues",
        "outline_items", "timeline_tracks", "timeline_events",
        "timeline_edges", "graph_nodes", "graph_edges",
        # P1
        "chapter_characters", "chapter_settings", "chapter_clues",
        "clue_characters", "clue_settings",
        "timeline_event_characters", "timeline_event_settings", "timeline_event_clues",
        "outline_item_characters", "outline_item_settings", "outline_item_clues",
        "outline_item_timeline_events",
    }
    assert set(SYNC_ENTITY_MODELS.keys()) == expected
    assert len(SYNC_ENTITY_MODELS) == 24


def test_sync_apply_order_respects_fk():
    """Apply order must respect FK dependencies (P0 before P1)."""
    expected = [
        # P0
        "projects", "volumes", "chapters",
        "characters", "setting_items", "clues",
        "outline_items", "timeline_tracks", "timeline_events",
        "timeline_edges", "graph_nodes", "graph_edges",
        # P1
        "chapter_characters", "chapter_settings", "chapter_clues",
        "clue_characters", "clue_settings",
        "timeline_event_characters", "timeline_event_settings", "timeline_event_clues",
        "outline_item_characters", "outline_item_settings", "outline_item_clues",
        "outline_item_timeline_events",
    ]
    assert SYNC_APPLY_ORDER == expected


def test_sync_delete_order_reverse():
    """Delete order must be reverse of apply order."""
    assert SYNC_DELETE_ORDER == list(reversed(SYNC_APPLY_ORDER))


def test_chapter_versions_not_in_sync_registry():
    """chapter_versions excluded from incremental sync — covered by local snapshots + full backup."""
    assert "chapter_versions" not in SYNC_ENTITY_MODELS
    assert "chapter_versions" not in SYNC_APPLY_ORDER
    assert "chapter_versions" not in SYNC_DELETE_ORDER
    assert "chapter_versions" not in _EXCLUDE_FIELDS


# ── Serialize project ──────────────────────────────────────────


def test_serialize_project(db_session):
    proj = Project(
        id=str(uuid4()),
        title="测试项目",
        author="作者",
        genre="玄幻",
        summary="简介",
        tags='["标签1"]',
        cover_image_path="/local/path/cover.png",
        status="writing",
        target_word_count=100000,
    )
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)

    payload = serialize_entity(proj, "projects")

    assert payload["id"] == proj.id
    assert payload["title"] == "测试项目"
    assert payload["author"] == "作者"
    assert payload["genre"] == "玄幻"
    assert payload["status"] == "writing"
    # cover_image_path must be cleared (local-only)
    assert payload["cover_image_path"] is None
    # Timestamps are ISO 8601 strings
    assert isinstance(payload["created_at"], str)
    assert "T" in payload["created_at"]


def test_serialize_project_cover_path_not_leaked(db_session):
    """cover_image_path must never contain the local file path."""
    proj = Project(
        id=str(uuid4()),
        title="项目",
        cover_image_path="C:\\Users\\secret\\cover.png",
    )
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)

    payload = serialize_entity(proj, "projects")
    assert payload["cover_image_path"] is None
    assert "secret" not in payload_to_json(payload)


# ── Serialize volume ───────────────────────────────────────────


def test_serialize_volume(db_session):
    proj = Project(id=str(uuid4()), title="项目")
    db_session.add(proj)
    db_session.commit()

    vol = Volume(
        id=str(uuid4()),
        project_id=proj.id,
        title="第一卷",
        order_index=0,
    )
    db_session.add(vol)
    db_session.commit()
    db_session.refresh(vol)

    payload = serialize_entity(vol, "volumes")
    assert payload["id"] == vol.id
    assert payload["project_id"] == proj.id
    assert payload["title"] == "第一卷"
    assert payload["order_index"] == 0
    assert isinstance(payload["created_at"], str)


# ── Serialize chapter ──────────────────────────────────────────


def test_serialize_chapter(db_session):
    proj = Project(id=str(uuid4()), title="项目")
    vol = Volume(id=str(uuid4()), project_id=proj.id, title="卷", order_index=0)
    db_session.add_all([proj, vol])
    db_session.commit()

    chap = Chapter(
        id=str(uuid4()),
        project_id=proj.id,
        volume_id=vol.id,
        title="第一章",
        content="正文内容",
        order_index=0,
        status="draft",
        word_count=4,
    )
    db_session.add(chap)
    db_session.commit()
    db_session.refresh(chap)

    payload = serialize_entity(chap, "chapters")
    assert payload["id"] == chap.id
    assert payload["title"] == "第一章"
    assert payload["content"] == "正文内容"
    assert payload["word_count"] == 4
    assert payload["status"] == "draft"


# ── Serialize soft-deleted entity ──────────────────────────────


def test_serialize_soft_deleted_chapter(db_session):
    proj = Project(id=str(uuid4()), title="项目")
    db_session.add(proj)
    db_session.commit()

    chap = Chapter(
        id=str(uuid4()),
        project_id=proj.id,
        title="已删除章节",
        content="",
        order_index=0,
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(chap)
    db_session.commit()
    db_session.refresh(chap)

    payload = serialize_entity(chap, "chapters")
    assert payload["deleted_at"] is not None
    assert isinstance(payload["deleted_at"], str)


# ── Deserialize ────────────────────────────────────────────────


def test_deserialize_project(db_session):
    payload = {
        "id": str(uuid4()),
        "title": "导入项目",
        "author": "作者",
        "genre": "玄幻",
        "summary": "简介",
        "tags": "[]",
        "cover_image_path": None,
        "status": "planning",
        "target_word_count": None,
        "created_at": "2026-05-30T10:00:00+00:00",
        "updated_at": "2026-05-30T10:00:00+00:00",
        "deleted_at": None,
        "version": 1,
    }
    kwargs = deserialize_entity(payload, "projects")
    assert kwargs["title"] == "导入项目"
    assert isinstance(kwargs["created_at"], datetime)


def test_deserialize_chapter(db_session):
    payload = {
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "volume_id": None,
        "title": "第一章",
        "content": "正文内容",
        "order_index": 0,
        "status": "draft",
        "word_count": 4,
        "created_at": "2026-05-30T10:00:00+00:00",
        "updated_at": "2026-05-30T10:00:00+00:00",
        "deleted_at": None,
        "version": 1,
    }
    kwargs = deserialize_entity(payload, "chapters")
    assert kwargs["title"] == "第一章"
    assert kwargs["content"] == "正文内容"
    assert isinstance(kwargs["created_at"], datetime)


def test_deserialize_drops_unknown_fields():
    """Unknown fields in payload should be silently dropped."""
    payload = {
        "id": str(uuid4()),
        "title": "测试",
        "nonexistent_field": "should be dropped",
    }
    kwargs = deserialize_entity(payload, "projects")
    assert "nonexistent_field" not in kwargs


def test_deserialize_unknown_entity_type():
    """Unknown entity type should return original payload."""
    payload = {"id": "test", "name": "unknown"}
    kwargs = deserialize_entity(payload, "knowledge_items")
    assert kwargs == payload


# ── get_entity_by_id / get_active_entity ───────────────────────


def test_get_entity_by_id(db_session):
    proj = Project(id=str(uuid4()), title="项目")
    db_session.add(proj)
    db_session.commit()

    result = get_entity_by_id(db_session, "projects", proj.id)
    assert result is not None
    assert result.id == proj.id


def test_get_active_entity_excludes_deleted(db_session):
    proj = Project(id=str(uuid4()), title="项目")
    db_session.add(proj)
    db_session.commit()

    chap = Chapter(
        id=str(uuid4()),
        project_id=proj.id,
        title="已删除",
        content="",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(chap)
    db_session.commit()

    result = get_active_entity(db_session, "chapters", chap.id)
    assert result is None


# ── Canonical JSON ─────────────────────────────────────────────


def test_payload_to_json_is_canonical():
    """JSON output should be deterministic (sorted keys)."""
    payload = {"b": 2, "a": 1}
    result = payload_to_json(payload)
    assert result == '{"a": 1, "b": 2}'


def test_payload_to_json_handles_chinese():
    """Chinese characters must be preserved (not escaped)."""
    payload = {"title": "测试项目"}
    result = payload_to_json(payload)
    assert "测试项目" in result


# ── L2 entity serialize/deserialize ────────────────────────────


def _seed_project(db_session) -> Project:
    proj = Project(id=str(uuid4()), title="项目")
    db_session.add(proj)
    db_session.commit()
    return proj


def test_serialize_character(db_session):
    proj = _seed_project(db_session)
    char = Character(
        id=str(uuid4()),
        project_id=proj.id,
        name="主角",
        role="protagonist",
        importance="major",
        status="active",
    )
    db_session.add(char)
    db_session.commit()
    db_session.refresh(char)

    payload = serialize_entity(char, "characters")
    assert payload["name"] == "主角"
    assert payload["role"] == "protagonist"
    assert isinstance(payload["created_at"], str)

    kwargs = deserialize_entity(payload, "characters")
    assert kwargs["name"] == "主角"
    assert isinstance(kwargs["created_at"], datetime)


def test_serialize_setting_item(db_session):
    proj = _seed_project(db_session)
    setting = SettingItem(
        id=str(uuid4()),
        project_id=proj.id,
        parent_id=None,
        title="设定页",
        item_type="custom",
        canon_status="confirmed",
        node_kind="page",
    )
    db_session.add(setting)
    db_session.commit()
    db_session.refresh(setting)

    payload = serialize_entity(setting, "setting_items")
    assert payload["title"] == "设定页"
    assert payload["node_kind"] == "page"

    kwargs = deserialize_entity(payload, "setting_items")
    assert kwargs["title"] == "设定页"
    assert isinstance(kwargs["created_at"], datetime)


def test_serialize_clue(db_session):
    proj = _seed_project(db_session)
    clue = Clue(
        id=str(uuid4()),
        project_id=proj.id,
        title="伏笔A",
        status="planted",
        visibility="hidden",
        importance="major",
    )
    db_session.add(clue)
    db_session.commit()
    db_session.refresh(clue)

    payload = serialize_entity(clue, "clues")
    assert payload["title"] == "伏笔A"
    assert payload["status"] == "planted"

    kwargs = deserialize_entity(payload, "clues")
    assert kwargs["title"] == "伏笔A"


def test_serialize_outline_item(db_session):
    proj = _seed_project(db_session)
    outline = OutlineItem(
        id=str(uuid4()),
        project_id=proj.id,
        parent_id=None,
        title="大纲条目",
        item_type="arc",
        status="planned",
        order_index=0,
    )
    db_session.add(outline)
    db_session.commit()
    db_session.refresh(outline)

    payload = serialize_entity(outline, "outline_items")
    assert payload["title"] == "大纲条目"
    assert payload["parent_id"] is None

    kwargs = deserialize_entity(payload, "outline_items")
    assert kwargs["title"] == "大纲条目"


def test_serialize_timeline_track(db_session):
    proj = _seed_project(db_session)
    track = TimelineTrack(
        id=str(uuid4()),
        project_id=proj.id,
        title="主线",
        track_type="main",
        is_main=True,
        order_index=0,
    )
    db_session.add(track)
    db_session.commit()
    db_session.refresh(track)

    payload = serialize_entity(track, "timeline_tracks")
    assert payload["title"] == "主线"
    assert payload["is_main"] is True

    kwargs = deserialize_entity(payload, "timeline_tracks")
    assert kwargs["title"] == "主线"


def test_serialize_timeline_event(db_session):
    proj = _seed_project(db_session)
    track = TimelineTrack(
        id=str(uuid4()), project_id=proj.id, title="主线",
        track_type="main", is_main=True, order_index=0,
    )
    db_session.add(track)
    db_session.commit()

    event = TimelineEvent(
        id=str(uuid4()),
        project_id=proj.id,
        track_id=track.id,
        title="事件A",
        event_type="plot",
        order_index=0,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    payload = serialize_entity(event, "timeline_events")
    assert payload["title"] == "事件A"
    assert payload["track_id"] == track.id

    kwargs = deserialize_entity(payload, "timeline_events")
    assert kwargs["track_id"] == track.id


def test_serialize_timeline_edge(db_session):
    proj = _seed_project(db_session)
    edge = TimelineEdge(
        id=str(uuid4()),
        project_id=proj.id,
        from_event_id="ev-1",
        to_event_id="ev-2",
        edge_type="causal",
    )
    db_session.add(edge)
    db_session.commit()
    db_session.refresh(edge)

    payload = serialize_entity(edge, "timeline_edges")
    assert payload["from_event_id"] == "ev-1"
    assert payload["edge_type"] == "causal"

    kwargs = deserialize_entity(payload, "timeline_edges")
    assert kwargs["from_event_id"] == "ev-1"


def test_serialize_graph_node(db_session):
    proj = _seed_project(db_session)
    node = GraphNode(
        id=str(uuid4()),
        project_id=proj.id,
        title="节点A",
        node_type="character",
        bound_type="character",
        bound_id="char-1",
        x=100.0,
        y=200.0,
    )
    db_session.add(node)
    db_session.commit()
    db_session.refresh(node)

    payload = serialize_entity(node, "graph_nodes")
    assert payload["title"] == "节点A"
    assert payload["bound_type"] == "character"
    assert payload["bound_id"] == "char-1"

    kwargs = deserialize_entity(payload, "graph_nodes")
    assert kwargs["bound_id"] == "char-1"


def test_serialize_graph_edge(db_session):
    proj = _seed_project(db_session)
    edge = GraphEdge(
        id=str(uuid4()),
        project_id=proj.id,
        from_node_id="gn-1",
        to_node_id="gn-2",
        relation_type="ally",
        direction="bidirectional",
    )
    db_session.add(edge)
    db_session.commit()
    db_session.refresh(edge)

    payload = serialize_entity(edge, "graph_edges")
    assert payload["from_node_id"] == "gn-1"
    assert payload["relation_type"] == "ally"

    kwargs = deserialize_entity(payload, "graph_edges")
    assert kwargs["relation_type"] == "ally"


def test_apply_order_dependency_check():
    """Verify that dependent entities come after their dependencies in apply order."""
    order_index = {name: i for i, name in enumerate(SYNC_APPLY_ORDER)}
    # P0 dependencies
    assert order_index["projects"] < order_index["volumes"]
    assert order_index["volumes"] < order_index["chapters"]
    assert order_index["volumes"] < order_index["outline_items"]
    assert order_index["chapters"] < order_index["outline_items"]
    assert order_index["timeline_tracks"] < order_index["timeline_events"]
    assert order_index["chapters"] < order_index["timeline_events"]
    assert order_index["timeline_events"] < order_index["timeline_edges"]
    assert order_index["graph_nodes"] < order_index["graph_edges"]
    # P1 dependencies: all P1 must come after all P0
    p0_types = {
        "projects", "volumes", "chapters", "characters", "setting_items", "clues",
        "outline_items", "timeline_tracks", "timeline_events", "timeline_edges",
        "graph_nodes", "graph_edges",
    }
    p1_types = {
        "chapter_characters", "chapter_settings", "chapter_clues",
        "clue_characters", "clue_settings",
        "timeline_event_characters", "timeline_event_settings", "timeline_event_clues",
        "outline_item_characters", "outline_item_settings", "outline_item_clues",
        "outline_item_timeline_events",
    }
    max_p0_index = max(order_index[t] for t in p0_types)
    min_p1_index = min(order_index[t] for t in p1_types)
    assert max_p0_index < min_p1_index


# ── L3 P1 join entity tests ─────────────────────────────────────

from app.models.chapter_character import ChapterCharacter  # noqa: E402
from app.models.timeline_event_character import TimelineEventCharacter  # noqa: E402
from app.models.outline_item_timeline_event import OutlineItemTimelineEvent  # noqa: E402


def test_serialize_chapter_character(db_session):
    proj = _seed_project(db_session)
    char = Character(
        id=str(uuid4()), project_id=proj.id, name="角色",
        role="supporting", importance="minor", status="active",
    )
    db_session.add(char)
    db_session.commit()

    vol = Volume(id=str(uuid4()), project_id=proj.id, title="卷", order_index=0)
    chap = Chapter(
        id=str(uuid4()), project_id=proj.id, volume_id=vol.id,
        title="章", content="", order_index=0, status="draft", word_count=0,
    )
    db_session.add_all([vol, chap])
    db_session.commit()

    link = ChapterCharacter(
        id=str(uuid4()),
        project_id=proj.id,
        chapter_id=chap.id,
        character_id=char.id,
        relation_type="appears",
        note="出场",
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)

    payload = serialize_entity(link, "chapter_characters")
    assert payload["chapter_id"] == chap.id
    assert payload["character_id"] == char.id
    assert payload["relation_type"] == "appears"
    assert "deleted_at" in payload
    assert "version" in payload

    kwargs = deserialize_entity(payload, "chapter_characters")
    assert kwargs["chapter_id"] == chap.id
    assert isinstance(kwargs["created_at"], datetime)


def test_serialize_timeline_event_character(db_session):
    proj = _seed_project(db_session)
    link = TimelineEventCharacter(
        id=str(uuid4()),
        project_id=proj.id,
        timeline_event_id="ev-1",
        character_id="char-1",
        relation_type="participant",
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)

    payload = serialize_entity(link, "timeline_event_characters")
    assert payload["timeline_event_id"] == "ev-1"
    assert payload["character_id"] == "char-1"
    assert "deleted_at" in payload

    kwargs = deserialize_entity(payload, "timeline_event_characters")
    assert kwargs["timeline_event_id"] == "ev-1"


def test_serialize_outline_item_timeline_event(db_session):
    proj = _seed_project(db_session)
    link = OutlineItemTimelineEvent(
        id=str(uuid4()),
        project_id=proj.id,
        outline_item_id="oi-1",
        timeline_event_id="ev-1",
        relation_type="related",
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)

    payload = serialize_entity(link, "outline_item_timeline_events")
    assert payload["outline_item_id"] == "oi-1"
    assert payload["timeline_event_id"] == "ev-1"
    assert "deleted_at" in payload

    kwargs = deserialize_entity(payload, "outline_item_timeline_events")
    assert kwargs["outline_item_id"] == "oi-1"
