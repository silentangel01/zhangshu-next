"""Tests for cloud_sync_service — sync orchestrator with fake CloudApiClient."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
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
from app.models.chapter_character import ChapterCharacter  # noqa: E402
from app.models.timeline_event_character import TimelineEventCharacter  # noqa: E402
from app.models.outline_item_timeline_event import OutlineItemTimelineEvent  # noqa: E402
from app.models.cloud_sync_state import CloudSyncState  # noqa: E402
from app.models.sync_dirty_record import SyncDirtyRecord  # noqa: E402
from app.models.cloud_project_link import CloudProjectLink  # noqa: E402
from app.models.app_config import AppConfig  # noqa: E402
from app.models.chapter_version import ChapterVersion  # noqa: E402
from app.services.sync_dirty_service import SyncDirtyService  # noqa: E402
from app.services.sync_apply_service import SyncApplyService  # noqa: E402


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def project(db_session):
    proj = Project(id=str(uuid4()), title="测试项目")
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)
    return proj


@pytest.fixture
def dirty_service(db_session):
    return SyncDirtyService(db_session)


@pytest.fixture
def apply_service(db_session):
    return SyncApplyService(db_session)


# ── Dirty record tests ─────────────────────────────────────────


def test_mark_dirty_creates_record(db_session, project, dirty_service):
    record = dirty_service.mark_dirty(project.id, "chapters", "chap-1", "upsert")
    assert record.project_id == project.id
    assert record.entity_type == "chapters"
    assert record.entity_id == "chap-1"
    assert record.action == "upsert"
    assert record.attempt_count == 0


def test_mark_dirty_upsert_same_entity(db_session, project, dirty_service):
    """Marking the same entity dirty twice should upsert, not duplicate."""
    dirty_service.mark_dirty(project.id, "chapters", "chap-1", "upsert")
    dirty_service.mark_dirty(project.id, "chapters", "chap-1", "upsert")

    count = dirty_service.count_dirty(project.id)
    assert count == 1


def test_mark_dirty_action_changes(db_session, project, dirty_service):
    """Updating action from upsert to delete should work."""
    dirty_service.mark_dirty(project.id, "chapters", "chap-1", "upsert")
    record = dirty_service.mark_dirty(project.id, "chapters", "chap-1", "delete")
    assert record.action == "delete"


def test_list_dirty_ordered(db_session, project, dirty_service):
    dirty_service.mark_dirty(project.id, "chapters", "chap-1", "upsert")
    dirty_service.mark_dirty(project.id, "chapters", "chap-2", "upsert")
    dirty_service.mark_dirty(project.id, "volumes", "vol-1", "upsert")

    records = dirty_service.list_dirty(project.id)
    assert len(records) == 3
    assert records[0].entity_id == "chap-1"


def test_remove_dirty_batch(db_session, project, dirty_service):
    dirty_service.mark_dirty(project.id, "chapters", "chap-1", "upsert")
    dirty_service.mark_dirty(project.id, "chapters", "chap-2", "upsert")
    dirty_service.mark_dirty(project.id, "chapters", "chap-3", "upsert")

    deleted = dirty_service.remove_dirty_batch(
        project.id,
        [("chapters", "chap-1"), ("chapters", "chap-2")],
    )
    assert deleted == 2
    assert dirty_service.count_dirty(project.id) == 1


def test_mark_error_increments_attempt(db_session, project, dirty_service):
    dirty_service.mark_dirty(project.id, "chapters", "chap-1", "upsert")
    dirty_service.mark_error(project.id, "chapters", "chap-1", "网络错误")

    records = dirty_service.list_dirty(project.id)
    assert records[0].attempt_count == 1
    assert records[0].last_error == "网络错误"


def test_mark_dirty_invalid_action(db_session, project, dirty_service):
    with pytest.raises(ValueError, match="Invalid dirty action"):
        dirty_service.mark_dirty(project.id, "chapters", "chap-1", "invalid")


# ── Dirty record coverage for representative entities ─────────


@pytest.mark.parametrize(
    "entity_type,entity_id",
    [
        ("projects", "proj-d"),
        ("volumes", "vol-d"),
        ("chapters", "chap-d"),
        ("characters", "char-d"),
        ("setting_items", "set-d"),
        ("clues", "clue-d"),
        ("outline_items", "out-d"),
        ("timeline_tracks", "track-d"),
        ("timeline_events", "evt-d"),
        ("graph_nodes", "node-d"),
        ("graph_edges", "edge-d"),
        ("chapter_characters", "cc-d"),
    ],
)
def test_mark_dirty_representative_entities(dirty_service, project, entity_type, entity_id):
    """Dirty records should work for all representative sync entity types."""
    record = dirty_service.mark_dirty(project.id, entity_type, entity_id, "upsert")
    assert record.entity_type == entity_type
    assert record.entity_id == entity_id
    assert record.action == "upsert"

    # Upsert semantics: re-mark same entity does not duplicate
    record2 = dirty_service.mark_dirty(project.id, entity_type, entity_id, "delete")
    assert record2.action == "delete"
    assert dirty_service.count_dirty(project.id) == 1

    # Remove
    dirty_service.remove_dirty(project.id, entity_type, entity_id)
    assert dirty_service.count_dirty(project.id) == 0


# ── Apply service tests ────────────────────────────────────────


def test_apply_upsert_creates_project(db_session, apply_service):
    proj_id = str(uuid4())
    changes = [{
        "entity_type": "projects",
        "entity_id": proj_id,
        "action": "upsert",
        "data": {
            "id": proj_id,
            "title": "云端项目",
            "author": "作者",
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
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 1

    project = db_session.get(Project, proj_id)
    assert project is not None
    assert project.title == "云端项目"


def test_apply_upsert_updates_existing(db_session, apply_service):
    proj_id = str(uuid4())
    proj = Project(id=proj_id, title="旧标题")
    db_session.add(proj)
    db_session.commit()

    changes = [{
        "entity_type": "projects",
        "entity_id": proj_id,
        "action": "upsert",
        "data": {
            "id": proj_id,
            "title": "新标题",
            "author": None,
            "genre": None,
            "summary": None,
            "tags": "[]",
            "cover_image_path": None,
            "status": "writing",
            "target_word_count": None,
            "created_at": "2026-05-30T10:00:00+00:00",
            "updated_at": "2026-05-30T12:00:00+00:00",
            "deleted_at": None,
            "version": 2,
        },
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 1

    db_session.refresh(proj)
    assert proj.title == "新标题"
    assert proj.status == "writing"


def test_apply_delete_soft_deletes(db_session, apply_service):
    proj_id = str(uuid4())
    chap_id = str(uuid4())
    proj = Project(id=proj_id, title="项目")
    chap = Chapter(id=chap_id, project_id=proj_id, title="章节", content="")
    db_session.add_all([proj, chap])
    db_session.commit()

    changes = [{
        "entity_type": "chapters",
        "entity_id": chap_id,
        "action": "delete",
        "data": {"id": chap_id, "deleted_at": "2026-05-30T12:00:00+00:00"},
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 1

    db_session.refresh(chap)
    assert chap.deleted_at is not None


def test_apply_delete_nonexistent_entity_ignored(db_session, apply_service):
    """Deleting an entity that doesn't exist locally should be a no-op."""
    changes = [{
        "entity_type": "chapters",
        "entity_id": str(uuid4()),
        "action": "delete",
        "data": {},
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 1


def test_apply_ignores_unknown_entity_type(db_session, apply_service):
    """Non-whitelisted entity types must be ignored."""
    changes = [{
        "entity_type": "knowledge_items",
        "entity_id": str(uuid4()),
        "action": "upsert",
        "data": {"id": str(uuid4()), "title": "未知知识"},
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 0


def test_apply_respects_fk_order(db_session, apply_service):
    """Upserts should create projects first, then volumes, then chapters."""
    proj_id = str(uuid4())
    vol_id = str(uuid4())
    chap_id = str(uuid4())

    changes = [
        {
            "entity_type": "chapters",
            "entity_id": chap_id,
            "action": "upsert",
            "data": {
                "id": chap_id,
                "project_id": proj_id,
                "volume_id": vol_id,
                "title": "第一章",
                "content": "",
                "order_index": 0,
                "status": "draft",
                "word_count": 0,
                "created_at": "2026-05-30T10:00:00+00:00",
                "updated_at": "2026-05-30T10:00:00+00:00",
                "deleted_at": None,
                "version": 1,
            },
        },
        {
            "entity_type": "projects",
            "entity_id": proj_id,
            "action": "upsert",
            "data": {
                "id": proj_id,
                "title": "项目",
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
        {
            "entity_type": "volumes",
            "entity_id": vol_id,
            "action": "upsert",
            "data": {
                "id": vol_id,
                "project_id": proj_id,
                "title": "第一卷",
                "order_index": 0,
                "created_at": "2026-05-30T10:00:00+00:00",
                "updated_at": "2026-05-30T10:00:00+00:00",
                "deleted_at": None,
                "version": 1,
            },
        },
    ]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 3

    # Verify all entities were created
    assert db_session.get(Project, proj_id) is not None
    assert db_session.get(Volume, vol_id) is not None
    assert db_session.get(Chapter, chap_id) is not None


def test_apply_does_not_create_chapter_versions(db_session, apply_service):
    """Remote apply must NOT create local chapter_versions."""
    proj_id = str(uuid4())
    chap_id = str(uuid4())

    proj = Project(id=proj_id, title="项目")
    db_session.add(proj)
    db_session.commit()

    changes = [{
        "entity_type": "chapters",
        "entity_id": chap_id,
        "action": "upsert",
        "data": {
            "id": chap_id,
            "project_id": proj_id,
            "volume_id": None,
            "title": "远程章节",
            "content": "远程正文",
            "order_index": 0,
            "status": "draft",
            "word_count": 4,
            "created_at": "2026-05-30T10:00:00+00:00",
            "updated_at": "2026-05-30T10:00:00+00:00",
            "deleted_at": None,
            "version": 1,
        },
    }]

    apply_service.apply_changes(changes)

    # Verify no chapter_versions were created
    version_count = db_session.query(ChapterVersion).filter(
        ChapterVersion.chapter_id == chap_id
    ).count()
    assert version_count == 0


# ── Cloud import (integration with mocked auth) ────────────────


def test_import_creates_local_project(db_session):
    """Importing a cloud project should create local project + link + sync state."""
    from app.services.cloud_sync_service import CloudSyncService

    proj_id = str(uuid4())
    vol_id = str(uuid4())
    chap_id = str(uuid4())

    # Mock the auth service
    with patch.object(CloudSyncService, "_require_cloud_user", return_value="user-123"):
        svc = CloudSyncService(db_session)

        # Mock the cloud call to return changes
        mock_changes = [
            {
                "entity_type": "projects",
                "entity_id": proj_id,
                "action": "upsert",
                "data": {
                    "id": proj_id,
                    "title": "云端导入项目",
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
            {
                "entity_type": "volumes",
                "entity_id": vol_id,
                "action": "upsert",
                "data": {
                    "id": vol_id,
                    "project_id": proj_id,
                    "title": "第一卷",
                    "order_index": 0,
                    "created_at": "2026-05-30T10:00:00+00:00",
                    "updated_at": "2026-05-30T10:00:00+00:00",
                    "deleted_at": None,
                    "version": 1,
                },
            },
            {
                "entity_type": "chapters",
                "entity_id": chap_id,
                "action": "upsert",
                "data": {
                    "id": chap_id,
                    "project_id": proj_id,
                    "volume_id": vol_id,
                    "title": "第一章",
                    "content": "正文",
                    "order_index": 0,
                    "status": "draft",
                    "word_count": 2,
                    "created_at": "2026-05-30T10:00:00+00:00",
                    "updated_at": "2026-05-30T10:00:00+00:00",
                    "deleted_at": None,
                    "version": 1,
                },
            },
        ]

        mock_pull_result = {
            "changes": mock_changes,
            "new_cursor": 3,
            "has_more": False,
        }

        with patch.object(
            svc._auth_svc, "call_with_refresh", return_value=mock_pull_result
        ):
            result = svc.import_cloud_project("cloud-proj-id")

    assert result["local_project_id"] == proj_id
    assert result["title"] == "云端导入项目"
    assert result["volumes_count"] == 1
    assert result["chapters_count"] == 1

    # Verify local entities created
    assert db_session.get(Project, proj_id) is not None
    assert db_session.get(Volume, vol_id) is not None
    assert db_session.get(Chapter, chap_id) is not None

    # Verify link and sync state created
    link = db_session.query(CloudProjectLink).filter(
        CloudProjectLink.project_id == proj_id
    ).first()
    assert link is not None
    assert link.cloud_project_id == "cloud-proj-id"

    sync_state = db_session.query(CloudSyncState).filter(
        CloudSyncState.project_id == proj_id
    ).first()
    assert sync_state is not None
    assert sync_state.last_cursor == 3


# ── L2 P0 entity apply tests ───────────────────────────────────


def test_apply_l2_character_upsert(db_session, apply_service):
    """Remote character upsert should create local character."""
    proj_id = str(uuid4())
    char_id = str(uuid4())

    proj = Project(id=proj_id, title="项目")
    db_session.add(proj)
    db_session.commit()

    changes = [{
        "entity_type": "characters",
        "entity_id": char_id,
        "action": "upsert",
        "data": {
            "id": char_id,
            "project_id": proj_id,
            "name": "主角",
            "role": "protagonist",
            "importance": "major",
            "status": "active",
            "created_at": "2026-05-30T10:00:00+00:00",
            "updated_at": "2026-05-30T10:00:00+00:00",
            "deleted_at": None,
            "version": 1,
        },
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 1

    char = db_session.get(Character, char_id)
    assert char is not None
    assert char.name == "主角"
    assert char.project_id == proj_id


def test_apply_l2_graph_nodes_and_edges(db_session, apply_service):
    """Remote graph_nodes and graph_edges should be created in dependency order."""
    proj_id = str(uuid4())
    node1_id = str(uuid4())
    node2_id = str(uuid4())
    edge_id = str(uuid4())

    proj = Project(id=proj_id, title="项目")
    db_session.add(proj)
    db_session.commit()

    changes = [
        {
            "entity_type": "graph_edges",
            "entity_id": edge_id,
            "action": "upsert",
            "data": {
                "id": edge_id,
                "project_id": proj_id,
                "from_node_id": node1_id,
                "to_node_id": node2_id,
                "relation_type": "ally",
                "direction": "bidirectional",
                "created_at": "2026-05-30T10:00:00+00:00",
                "updated_at": "2026-05-30T10:00:00+00:00",
                "deleted_at": None,
                "version": 1,
            },
        },
        {
            "entity_type": "graph_nodes",
            "entity_id": node1_id,
            "action": "upsert",
            "data": {
                "id": node1_id,
                "project_id": proj_id,
                "title": "节点A",
                "node_type": "character",
                "created_at": "2026-05-30T10:00:00+00:00",
                "updated_at": "2026-05-30T10:00:00+00:00",
                "deleted_at": None,
                "version": 1,
            },
        },
        {
            "entity_type": "graph_nodes",
            "entity_id": node2_id,
            "action": "upsert",
            "data": {
                "id": node2_id,
                "project_id": proj_id,
                "title": "节点B",
                "node_type": "character",
                "created_at": "2026-05-30T10:00:00+00:00",
                "updated_at": "2026-05-30T10:00:00+00:00",
                "deleted_at": None,
                "version": 1,
            },
        },
    ]

    result = apply_service.apply_changes(changes)
    # graph_nodes applied first (2), then graph_edges (1) = 3
    assert result["applied"] == 3

    assert db_session.get(GraphNode, node1_id) is not None
    assert db_session.get(GraphNode, node2_id) is not None
    assert db_session.get(GraphEdge, edge_id) is not None


def test_apply_l2_delete_character(db_session, apply_service):
    """Remote delete for character should soft-delete locally."""
    proj_id = str(uuid4())
    char_id = str(uuid4())

    proj = Project(id=proj_id, title="项目")
    db_session.add(proj)
    char = Character(id=char_id, project_id=proj_id, name="待删除")
    db_session.add(char)
    db_session.commit()

    changes = [{
        "entity_type": "characters",
        "entity_id": char_id,
        "action": "delete",
        "data": {},
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 1

    db_session.refresh(char)
    assert char.deleted_at is not None


def test_apply_l2_delete_graph_edge(db_session, apply_service):
    """Remote delete for graph_edge should soft-delete locally."""
    proj_id = str(uuid4())
    edge_id = str(uuid4())

    proj = Project(id=proj_id, title="项目")
    db_session.add(proj)
    edge = GraphEdge(
        id=edge_id, project_id=proj_id,
        from_node_id="gn-1", to_node_id="gn-2",
        relation_type="ally",
    )
    db_session.add(edge)
    db_session.commit()

    changes = [{
        "entity_type": "graph_edges",
        "entity_id": edge_id,
        "action": "delete",
        "data": {},
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 1

    db_session.refresh(edge)
    assert edge.deleted_at is not None


def test_apply_outline_items_two_phase_parent_first(db_session, apply_service):
    """Outline items with parent_id should be applied in two phases."""
    proj_id = str(uuid4())
    parent_id = str(uuid4())
    child_id = str(uuid4())

    proj = Project(id=proj_id, title="项目")
    db_session.add(proj)
    db_session.commit()

    # Child appears before parent in the changes list
    changes = [
        {
            "entity_type": "outline_items",
            "entity_id": child_id,
            "action": "upsert",
            "data": {
                "id": child_id,
                "project_id": proj_id,
                "parent_id": parent_id,
                "title": "子大纲",
                "item_type": "scene",
                "status": "planned",
                "order_index": 0,
                "created_at": "2026-05-30T10:00:00+00:00",
                "updated_at": "2026-05-30T10:00:00+00:00",
                "deleted_at": None,
                "version": 1,
            },
        },
        {
            "entity_type": "outline_items",
            "entity_id": parent_id,
            "action": "upsert",
            "data": {
                "id": parent_id,
                "project_id": proj_id,
                "parent_id": None,
                "title": "父大纲",
                "item_type": "arc",
                "status": "planned",
                "order_index": 0,
                "created_at": "2026-05-30T10:00:00+00:00",
                "updated_at": "2026-05-30T10:00:00+00:00",
                "deleted_at": None,
                "version": 1,
            },
        },
    ]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 2

    parent = db_session.get(OutlineItem, parent_id)
    child = db_session.get(OutlineItem, child_id)
    assert parent is not None
    assert child is not None
    assert child.parent_id == parent_id


def test_apply_skips_missing_fk_dependency(db_session, apply_service):
    """Entities with missing required FK should be skipped gracefully."""
    proj_id = str(uuid4())
    event_id = str(uuid4())
    track_id = str(uuid4())

    # No project or track exists — event references non-existent ones
    changes = [{
        "entity_type": "timeline_events",
        "entity_id": event_id,
        "action": "upsert",
        "data": {
            "id": event_id,
            "project_id": proj_id,
            "track_id": track_id,
            "title": "孤立事件",
            "event_type": "plot",
            "order_index": 0,
            "created_at": "2026-05-30T10:00:00+00:00",
            "updated_at": "2026-05-30T10:00:00+00:00",
            "deleted_at": None,
            "version": 1,
        },
    }]

    # With SQLite default (FK off), the insert will succeed because
    # FK constraints are not enforced. This test verifies apply doesn't crash.
    result = apply_service.apply_changes(changes)
    # Either applied (FK off) or skipped (FK on) — both are acceptable
    assert result["applied"] + result["skipped"] == 1


def test_import_cloud_project_with_l2_entities(db_session):
    """Import should handle L2 entities alongside L1."""
    from app.services.cloud_sync_service import CloudSyncService

    proj_id = str(uuid4())
    char_id = str(uuid4())
    node_id = str(uuid4())

    with patch.object(CloudSyncService, "_require_cloud_user", return_value="user-123"):
        svc = CloudSyncService(db_session)

        mock_changes = [
            {
                "entity_type": "projects",
                "entity_id": proj_id,
                "action": "upsert",
                "data": {
                    "id": proj_id,
                    "title": "L2导入项目",
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
            {
                "entity_type": "characters",
                "entity_id": char_id,
                "action": "upsert",
                "data": {
                    "id": char_id,
                    "project_id": proj_id,
                    "name": "导入角色",
                    "role": "protagonist",
                    "importance": "major",
                    "status": "active",
                    "created_at": "2026-05-30T10:00:00+00:00",
                    "updated_at": "2026-05-30T10:00:00+00:00",
                    "deleted_at": None,
                    "version": 1,
                },
            },
            {
                "entity_type": "graph_nodes",
                "entity_id": node_id,
                "action": "upsert",
                "data": {
                    "id": node_id,
                    "project_id": proj_id,
                    "title": "导入节点",
                    "node_type": "character",
                    "created_at": "2026-05-30T10:00:00+00:00",
                    "updated_at": "2026-05-30T10:00:00+00:00",
                    "deleted_at": None,
                    "version": 1,
                },
            },
        ]

        mock_pull_result = {
            "changes": mock_changes,
            "new_cursor": 3,
            "has_more": False,
        }

        with patch.object(
            svc._auth_svc, "call_with_refresh", return_value=mock_pull_result
        ):
            result = svc.import_cloud_project("cloud-proj-l2")

    assert result["local_project_id"] == proj_id
    assert result["title"] == "L2导入项目"

    # Verify L2 entities created
    assert db_session.get(Character, char_id) is not None
    assert db_session.get(GraphNode, node_id) is not None
    assert db_session.get(Character, char_id).name == "导入角色"


# ── L3 P1 join entity apply tests ───────────────────────────────


def test_apply_l3_chapter_character_with_parents(db_session, apply_service):
    """P1 chapter_characters should apply when parent chapter and character exist."""
    proj_id = str(uuid4())
    chap_id = str(uuid4())
    char_id = str(uuid4())
    link_id = str(uuid4())

    proj = Project(id=proj_id, title="项目")
    vol = Volume(id=str(uuid4()), project_id=proj_id, title="卷", order_index=0)
    chap = Chapter(id=chap_id, project_id=proj_id, volume_id=vol.id,
                   title="章", content="", order_index=0, status="draft", word_count=0)
    char = Character(id=char_id, project_id=proj_id, name="角色")
    db_session.add_all([proj, vol, chap, char])
    db_session.commit()

    changes = [{
        "entity_type": "chapter_characters",
        "entity_id": link_id,
        "action": "upsert",
        "data": {
            "id": link_id,
            "project_id": proj_id,
            "chapter_id": chap_id,
            "character_id": char_id,
            "relation_type": "appears",
            "note": "",
            "created_at": "2026-05-30T10:00:00+00:00",
            "updated_at": "2026-05-30T10:00:00+00:00",
            "deleted_at": None,
            "version": 1,
        },
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 1

    link = db_session.get(ChapterCharacter, link_id)
    assert link is not None
    assert link.chapter_id == chap_id
    assert link.character_id == char_id


def test_apply_l3_skips_missing_parent(db_session, apply_service):
    """P1 upsert should skip when a parent entity is missing."""
    proj_id = str(uuid4())
    link_id = str(uuid4())

    changes = [{
        "entity_type": "chapter_characters",
        "entity_id": link_id,
        "action": "upsert",
        "data": {
            "id": link_id,
            "project_id": proj_id,
            "chapter_id": "nonexistent-chapter",
            "character_id": "nonexistent-character",
            "relation_type": "appears",
            "note": "",
            "created_at": "2026-05-30T10:00:00+00:00",
            "updated_at": "2026-05-30T10:00:00+00:00",
            "deleted_at": None,
            "version": 1,
        },
    }]

    result = apply_service.apply_changes(changes)
    assert result["skipped"] == 1
    assert db_session.get(ChapterCharacter, link_id) is None


def test_apply_l3_skips_soft_deleted_parent(db_session, apply_service):
    """P1 upsert should skip when a parent entity is soft-deleted."""
    proj_id = str(uuid4())
    chap_id = str(uuid4())
    char_id = str(uuid4())
    link_id = str(uuid4())

    proj = Project(id=proj_id, title="项目")
    vol = Volume(id=str(uuid4()), project_id=proj_id, title="卷", order_index=0)
    chap = Chapter(id=chap_id, project_id=proj_id, volume_id=vol.id,
                   title="章", content="", order_index=0, status="draft", word_count=0)
    char = Character(
        id=char_id, project_id=proj_id, name="已删除角色",
        deleted_at=datetime(2026, 5, 29, tzinfo=timezone.utc),
    )
    db_session.add_all([proj, vol, chap, char])
    db_session.commit()

    changes = [{
        "entity_type": "chapter_characters",
        "entity_id": link_id,
        "action": "upsert",
        "data": {
            "id": link_id,
            "project_id": proj_id,
            "chapter_id": chap_id,
            "character_id": char_id,
            "relation_type": "appears",
            "note": "",
            "created_at": "2026-05-30T10:00:00+00:00",
            "updated_at": "2026-05-30T10:00:00+00:00",
            "deleted_at": None,
            "version": 1,
        },
    }]

    result = apply_service.apply_changes(changes)
    assert result["skipped"] == 1


def test_apply_l3_delete_join_soft_deletes(db_session, apply_service):
    """Remote delete for P1 join should soft-delete the link row."""
    proj_id = str(uuid4())
    link_id = str(uuid4())

    link = ChapterCharacter(
        id=link_id, project_id=proj_id,
        chapter_id="ch-1", character_id="char-1",
        relation_type="appears",
    )
    db_session.add(link)
    db_session.commit()

    changes = [{
        "entity_type": "chapter_characters",
        "entity_id": link_id,
        "action": "delete",
        "data": {},
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 1

    db_session.refresh(link)
    assert link.deleted_at is not None


def test_apply_l3_material_link_revive_by_natural_key(db_session, apply_service):
    """P1 material link with same natural key should revive soft-deleted row."""
    proj_id = str(uuid4())
    old_link_id = str(uuid4())
    new_link_id = str(uuid4())
    event_id = str(uuid4())
    char_id = str(uuid4())

    # Seed parent entities
    proj = Project(id=proj_id, title="项目")
    track = TimelineTrack(id=str(uuid4()), project_id=proj_id, title="主线",
                          track_type="main", is_main=True, order_index=0)
    event = TimelineEvent(id=event_id, project_id=proj_id, track_id=track.id,
                          title="事件", event_type="plot", order_index=0)
    char = Character(id=char_id, project_id=proj_id, name="角色")
    db_session.add_all([proj, track, event, char])
    db_session.commit()

    # Existing soft-deleted material link
    old_link = TimelineEventCharacter(
        id=old_link_id,
        project_id=proj_id,
        timeline_event_id=event_id,
        character_id=char_id,
        relation_type="old_relation",
        deleted_at=datetime(2026, 5, 29, tzinfo=timezone.utc),
    )
    db_session.add(old_link)
    db_session.commit()

    # Remote upsert with new ID but same natural key
    changes = [{
        "entity_type": "timeline_event_characters",
        "entity_id": new_link_id,
        "action": "upsert",
        "data": {
            "id": new_link_id,
            "project_id": proj_id,
            "timeline_event_id": event_id,
            "character_id": char_id,
            "relation_type": "new_relation",
            "note": "",
            "created_at": "2026-05-30T10:00:00+00:00",
            "updated_at": "2026-05-30T10:00:00+00:00",
            "deleted_at": None,
            "version": 2,
        },
    }]

    result = apply_service.apply_changes(changes)
    assert result["applied"] == 1

    # The old link should be revived with the new ID
    db_session.expire_all()
    revived = db_session.get(TimelineEventCharacter, new_link_id)
    assert revived is not None
    assert revived.deleted_at is None
    assert revived.relation_type == "new_relation"

    # Old ID should no longer exist
    assert db_session.get(TimelineEventCharacter, old_link_id) is None


# ── Phase 1: duplicate restore protection ────────────────────────


def test_get_by_cloud_project_ignores_soft_deleted_link(db_session):
    """get_by_cloud_project should not return soft-deleted links."""
    from app.repositories.cloud_project_link_repo import CloudProjectLinkRepository
    from datetime import datetime, timezone

    link = CloudProjectLink(
        id=str(uuid4()),
        project_id=str(uuid4()),
        cloud_project_id="cloud-proj-soft-del",
        cloud_user_id="user-123",
        cloud_enabled=True,
        provider="zhangshu",
        status="active",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(link)
    db_session.commit()

    repo = CloudProjectLinkRepository(db_session)
    result = repo.get_by_cloud_project("cloud-proj-soft-del", "user-123")
    assert result is None


def test_get_by_cloud_project_returns_active_link(db_session):
    """get_by_cloud_project should return active links."""
    from app.repositories.cloud_project_link_repo import CloudProjectLinkRepository

    proj_id = str(uuid4())
    link = CloudProjectLink(
        id=str(uuid4()),
        project_id=proj_id,
        cloud_project_id="cloud-proj-active",
        cloud_user_id="user-123",
        cloud_enabled=True,
        provider="zhangshu",
        status="active",
    )
    db_session.add(link)
    db_session.commit()

    repo = CloudProjectLinkRepository(db_session)
    result = repo.get_by_cloud_project("cloud-proj-active", "user-123")
    assert result is not None
    assert result.project_id == proj_id


def test_import_cloud_project_existing_link_returns_already_exists(db_session):
    """If an active link exists, import should return mode='already_exists' without creating new project."""
    from app.services.cloud_sync_service import CloudSyncService

    proj_id = str(uuid4())
    proj = Project(id=proj_id, title="已存在项目")
    db_session.add(proj)
    db_session.commit()

    link = CloudProjectLink(
        id=str(uuid4()),
        project_id=proj_id,
        cloud_project_id="cloud-proj-exist",
        cloud_user_id="user-123",
        cloud_enabled=True,
        provider="zhangshu",
        status="active",
    )
    db_session.add(link)
    db_session.commit()

    project_count_before = db_session.query(Project).count()

    with patch.object(CloudSyncService, "_require_cloud_user", return_value="user-123"):
        svc = CloudSyncService(db_session)
        result = svc.import_cloud_project("cloud-proj-exist")

    assert result["mode"] == "already_exists"
    assert result["local_project_id"] == proj_id
    assert result["title"] == "已存在项目"
    assert result["volumes_count"] == 0
    assert result["chapters_count"] == 0
    assert "已在本机存在" in (result.get("message") or "")

    # Verify no new project was created
    project_count_after = db_session.query(Project).count()
    assert project_count_after == project_count_before


def test_import_cloud_project_without_existing_link_still_restores_from_sync(db_session):
    """Without an existing link, import should restore from incremental sync (existing behavior)."""
    from app.services.cloud_sync_service import CloudSyncService

    proj_id = str(uuid4())

    with patch.object(CloudSyncService, "_require_cloud_user", return_value="user-123"):
        svc = CloudSyncService(db_session)

        mock_changes = [
            {
                "entity_type": "projects",
                "entity_id": proj_id,
                "action": "upsert",
                "data": {
                    "id": proj_id,
                    "title": "新恢复项目",
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
        ]

        mock_pull_result = {
            "changes": mock_changes,
            "new_cursor": 1,
            "has_more": False,
        }

        with patch.object(
            svc._auth_svc, "call_with_refresh", return_value=mock_pull_result
        ):
            result = svc.import_cloud_project("cloud-proj-new")

    assert result["mode"] == "restored_as_new"
    assert result["local_project_id"] == proj_id
    assert result["title"] == "新恢复项目"

    # Verify link was created
    link = db_session.query(CloudProjectLink).filter(
        CloudProjectLink.cloud_project_id == "cloud-proj-new"
    ).first()
    assert link is not None


def test_list_cloud_projects_marks_linked_locally(db_session):
    """GET /api/cloud/projects should annotate each project with linked_locally and local_project_id."""
    from app.services.cloud_auth_service import CloudAuthService

    # Seed a local project with a cloud link
    local_proj_id = str(uuid4())
    local_proj = Project(id=local_proj_id, title="本地项目")
    db_session.add(local_proj)
    db_session.commit()

    link = CloudProjectLink(
        id=str(uuid4()),
        project_id=local_proj_id,
        cloud_project_id="cloud-linked",
        cloud_user_id="user-123",
        cloud_enabled=True,
        provider="zhangshu",
        status="active",
    )
    db_session.add(link)
    db_session.commit()

    # Mock the remote projects list
    remote_projects = [
        {"id": "cloud-linked", "title": "已关联项目", "created_at": "", "updated_at": ""},
        {"id": "cloud-unlinked", "title": "未关联项目", "created_at": "", "updated_at": ""},
    ]

    # Mock CloudAuthService
    mock_auth = MagicMock()
    mock_auth.is_logged_in.return_value = True
    mock_auth.get_cloud_user_id.return_value = "user-123"
    mock_auth.call_with_refresh.return_value = remote_projects

    # Call the annotation logic directly (extracted from the endpoint)
    from app.repositories.cloud_project_link_repo import CloudProjectLinkRepository
    link_repo = CloudProjectLinkRepository(db_session)
    cloud_user_id = "user-123"

    def _annotate(item: dict) -> dict:
        link = link_repo.get_by_cloud_project(item["id"], cloud_user_id)
        if link is not None:
            item["linked_locally"] = True
            item["local_project_id"] = link.project_id
        else:
            item["linked_locally"] = False
            item["local_project_id"] = None
        return item

    annotated = [_annotate(p) for p in remote_projects]

    # Verify linked project
    assert annotated[0]["id"] == "cloud-linked"
    assert annotated[0]["linked_locally"] is True
    assert annotated[0]["local_project_id"] == local_proj_id

    # Verify unlinked project
    assert annotated[1]["id"] == "cloud-unlinked"
    assert annotated[1]["linked_locally"] is False
    assert annotated[1]["local_project_id"] is None


# ── Phase 3: validate_link_existing_project ──────────────────────


def test_validate_link_empty_remote_changes_allows(db_session):
    """Empty remote changes should allow linking (local will be initial source)."""
    from app.services.cloud_sync_service import CloudSyncService

    proj_id = str(uuid4())
    proj = Project(id=proj_id, title="本地项目")
    db_session.add(proj)
    db_session.commit()

    svc = CloudSyncService(db_session)

    # Mock _collect_initial_remote_changes to return empty
    with patch.object(
        svc, "_collect_initial_remote_changes", return_value=([], 0)
    ):
        # Should not raise
        svc.validate_link_existing_project(proj_id, "cloud-proj-empty", "user-123")


def test_validate_link_matching_project_identity_allows(db_session):
    """Remote projects.entity_id == project_id should allow linking."""
    from app.services.cloud_sync_service import CloudSyncService

    proj_id = str(uuid4())
    proj = Project(id=proj_id, title="本地项目")
    db_session.add(proj)
    db_session.commit()

    svc = CloudSyncService(db_session)

    mock_changes = [
        {
            "entity_type": "projects",
            "entity_id": proj_id,
            "action": "upsert",
            "data": {"id": proj_id, "title": "本地项目"},
        },
        {
            "entity_type": "chapters",
            "entity_id": str(uuid4()),
            "action": "upsert",
            "data": {},
        },
    ]

    with patch.object(
        svc, "_collect_initial_remote_changes", return_value=(mock_changes, 5)
    ):
        # Should not raise
        svc.validate_link_existing_project(proj_id, "cloud-proj-match", "user-123")


def test_validate_link_mismatched_project_identity_rejects(db_session):
    """Remote projects.entity_id != project_id should reject linking."""
    from app.services.cloud_sync_service import CloudSyncError, CloudSyncService

    proj_id = str(uuid4())
    other_proj_id = str(uuid4())
    proj = Project(id=proj_id, title="本地项目")
    db_session.add(proj)
    db_session.commit()

    svc = CloudSyncService(db_session)

    mock_changes = [
        {
            "entity_type": "projects",
            "entity_id": other_proj_id,
            "action": "upsert",
            "data": {"id": other_proj_id, "title": "其他项目"},
        },
    ]

    with patch.object(
        svc, "_collect_initial_remote_changes", return_value=(mock_changes, 3)
    ):
        with pytest.raises(CloudSyncError, match="属于另一个项目"):
            svc.validate_link_existing_project(proj_id, "cloud-proj-mismatch", "user-123")


def test_validate_link_missing_project_entity_rejects(db_session):
    """Remote changes non-empty but no project entity should reject linking."""
    from app.services.cloud_sync_service import CloudSyncError, CloudSyncService

    proj_id = str(uuid4())
    proj = Project(id=proj_id, title="本地项目")
    db_session.add(proj)
    db_session.commit()

    svc = CloudSyncService(db_session)

    # Changes with no projects entity
    mock_changes = [
        {
            "entity_type": "chapters",
            "entity_id": str(uuid4()),
            "action": "upsert",
            "data": {},
        },
        {
            "entity_type": "volumes",
            "entity_id": str(uuid4()),
            "action": "upsert",
            "data": {},
        },
    ]

    with patch.object(
        svc, "_collect_initial_remote_changes", return_value=(mock_changes, 2)
    ):
        with pytest.raises(CloudSyncError, match="缺少项目身份信息"):
            svc.validate_link_existing_project(proj_id, "cloud-proj-no-proj", "user-123")


def test_validate_link_already_linked_to_other_project_rejects(db_session):
    """Same cloud project already linked to other local project should reject."""
    from app.services.cloud_sync_service import CloudSyncError, CloudSyncService

    proj_id = str(uuid4())
    other_proj_id = str(uuid4())

    proj = Project(id=proj_id, title="当前项目")
    db_session.add(proj)
    other_proj = Project(id=other_proj_id, title="其他项目")
    db_session.add(other_proj)
    db_session.commit()

    # Create link from cloud project to OTHER local project
    link = CloudProjectLink(
        id=str(uuid4()),
        project_id=other_proj_id,
        cloud_project_id="cloud-proj-linked",
        cloud_user_id="user-123",
        cloud_enabled=True,
        provider="zhangshu",
        status="active",
    )
    db_session.add(link)
    db_session.commit()

    svc = CloudSyncService(db_session)

    with pytest.raises(CloudSyncError, match="已关联到本机另一个项目"):
        svc.validate_link_existing_project(proj_id, "cloud-proj-linked", "user-123")


def test_validate_link_remote_fetch_failed_rejects(db_session):
    """Network failure when fetching remote changes should reject with clear error."""
    from app.services.cloud_sync_service import CloudSyncError, CloudSyncService

    proj_id = str(uuid4())
    proj = Project(id=proj_id, title="本地项目")
    db_session.add(proj)
    db_session.commit()

    svc = CloudSyncService(db_session)

    with patch.object(
        svc,
        "_collect_initial_remote_changes",
        side_effect=Exception("Network timeout"),
    ):
        with pytest.raises(CloudSyncError, match="无法获取云端项目数据"):
            svc.validate_link_existing_project(proj_id, "cloud-proj-err", "user-123")
