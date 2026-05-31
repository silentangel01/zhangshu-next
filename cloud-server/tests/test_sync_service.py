"""Tests for SyncService business logic."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base  # noqa: E402

import app.models.user  # noqa: E402, F401
import app.models.cloud_project  # noqa: E402, F401
import app.models.cloud_sync_entity  # noqa: E402, F401
import app.models.cloud_sync_change  # noqa: E402, F401
import app.models.cloud_sync_snapshot  # noqa: E402, F401
import app.models.cloud_sync_conflict  # noqa: E402, F401

from app.models.cloud_project import CloudProject  # noqa: E402
from app.schemas.sync import SyncChangeIn, SyncPushRequest  # noqa: E402
from app.services.sync_service import (  # noqa: E402
    SyncError,
    SyncService,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


def _seed_project(db_session: Session, user_id: str = "user-1") -> str:
    proj_id = "proj-1"
    proj = CloudProject(id=proj_id, owner_id=user_id, title="Test")
    db_session.add(proj)
    db_session.commit()
    return proj_id


# ── Push tests ───────────────────────────────────────────────────


def test_push_new_entity(db_session):
    proj_id = _seed_project(db_session)
    svc = SyncService(db_session)

    request = SyncPushRequest(
        cursor=0,
        changes=[
            SyncChangeIn(
                entity_type="chapters",
                entity_id="chap-1",
                action="upsert",
                data={"id": "chap-1", "title": "第一章"},
                local_version=1,
            )
        ],
    )
    result = svc.push(proj_id, "user-1", request)
    assert len(result.accepted) == 1
    assert result.accepted[0].cloud_version == 1
    assert result.new_cursor > 0


def test_push_update_increments_version(db_session):
    proj_id = _seed_project(db_session)
    svc = SyncService(db_session)

    # First push
    req1 = SyncPushRequest(
        cursor=0,
        changes=[
            SyncChangeIn(
                entity_type="chapters",
                entity_id="chap-1",
                action="upsert",
                data={"id": "chap-1", "title": "v1"},
                local_version=1,
            )
        ],
    )
    r1 = svc.push(proj_id, "user-1", req1)
    assert r1.accepted[0].cloud_version == 1

    # Second push with correct base version
    req2 = SyncPushRequest(
        cursor=r1.new_cursor,
        changes=[
            SyncChangeIn(
                entity_type="chapters",
                entity_id="chap-1",
                action="upsert",
                data={"id": "chap-1", "title": "v2"},
                base_cloud_version=1,
                local_version=2,
                local_updated_at="2026-05-30T11:00:00+00:00",
            )
        ],
    )
    r2 = svc.push(proj_id, "user-1", req2)
    assert r2.accepted[0].cloud_version == 2


def test_push_rejects_disallowed_entity_type(db_session):
    proj_id = _seed_project(db_session)
    svc = SyncService(db_session)

    request = SyncPushRequest(
        cursor=0,
        changes=[
            SyncChangeIn(
                entity_type="knowledge_items",
                entity_id="ki-1",
                action="upsert",
                data={"id": "ki-1", "title": "未知知识"},
            )
        ],
    )
    result = svc.push(proj_id, "user-1", request)
    assert len(result.rejected) == 1
    assert "不支持" in result.rejected[0].reason


def test_push_owner_isolation(db_session):
    proj_id = _seed_project(db_session, user_id="user-a")
    svc = SyncService(db_session)

    request = SyncPushRequest(
        cursor=0,
        changes=[
            SyncChangeIn(
                entity_type="chapters",
                entity_id="chap-1",
                action="upsert",
                data={"id": "chap-1", "title": "x"},
            )
        ],
    )
    with pytest.raises(SyncError, match="无权"):
        svc.push(proj_id, "user-b", request)


# ── Pull tests ───────────────────────────────────────────────────


def test_pull_returns_changes_after_cursor(db_session):
    proj_id = _seed_project(db_session)
    svc = SyncService(db_session)

    # Push 2 changes
    for i in range(1, 3):
        svc.push(
            proj_id,
            "user-1",
            SyncPushRequest(
                cursor=0,
                changes=[
                    SyncChangeIn(
                        entity_type="chapters",
                        entity_id=f"chap-{i}",
                        action="upsert",
                        data={"id": f"chap-{i}", "title": f"第{i}章"},
                    )
                ],
            ),
        )

    # Pull from cursor 0 → should get both
    result = svc.pull(proj_id, "user-1", cursor=0)
    assert len(result.changes) == 2

    # Pull from first cursor → should get only second
    result2 = svc.pull(proj_id, "user-1", cursor=result.changes[0].change_id)
    assert len(result2.changes) == 1
    assert result2.changes[0].entity_id == "chap-2"


def test_pull_has_more_pagination(db_session):
    proj_id = _seed_project(db_session)
    svc = SyncService(db_session)

    # Push 5 changes
    for i in range(5):
        svc.push(
            proj_id,
            "user-1",
            SyncPushRequest(
                cursor=0,
                changes=[
                    SyncChangeIn(
                        entity_type="chapters",
                        entity_id=f"chap-{i}",
                        action="upsert",
                        data={"id": f"chap-{i}", "title": f"第{i}章"},
                    )
                ],
            ),
        )

    # Pull with limit=3
    result = svc.pull(proj_id, "user-1", cursor=0, limit=3)
    assert len(result.changes) == 3
    assert result.has_more is True

    # Pull remaining
    result2 = svc.pull(proj_id, "user-1", cursor=result.new_cursor, limit=3)
    assert len(result2.changes) == 2
    assert result2.has_more is False


# ── Snapshot pruning ─────────────────────────────────────────────


def test_snapshot_pruning_keeps_recent_n(db_session):
    proj_id = _seed_project(db_session)
    svc = SyncService(db_session)

    # Push 12 versions of the same chapter
    for i in range(12):
        svc.push(
            proj_id,
            "user-1",
            SyncPushRequest(
                cursor=0,
                changes=[
                    SyncChangeIn(
                        entity_type="chapters",
                        entity_id="chap-1",
                        action="upsert",
                        data={"id": "chap-1", "title": f"v{i}"},
                        base_cloud_version=i,
                        local_version=i + 1,
                        local_updated_at=f"2026-05-30T{10 + i}:00:00+00:00",
                    )
                ],
            ),
        )

    # Should have at most 10 snapshots (default retention)
    from app.repositories.cloud_sync_repo import CloudSyncRepo

    repo = CloudSyncRepo(db_session)
    snaps = repo.list_snapshots(proj_id, "chapters", "chap-1", limit=100)
    assert len(snaps) <= 10


# ── L2 P0 entity tests ──────────────────────────────────────────


def test_push_character_entity(db_session):
    proj_id = _seed_project(db_session)
    svc = SyncService(db_session)

    request = SyncPushRequest(
        cursor=0,
        changes=[
            SyncChangeIn(
                entity_type="characters",
                entity_id="char-1",
                action="upsert",
                data={
                    "id": "char-1",
                    "project_id": proj_id,
                    "name": "主角",
                    "role": "protagonist",
                    "importance": "major",
                    "status": "active",
                },
                local_version=1,
            )
        ],
    )
    result = svc.push(proj_id, "user-1", request)
    assert len(result.accepted) == 1
    assert result.accepted[0].cloud_version == 1

    # Pull back and verify
    pull = svc.pull(proj_id, "user-1", cursor=0)
    assert len(pull.changes) == 1
    assert pull.changes[0].entity_type == "characters"
    assert pull.changes[0].data["name"] == "主角"


def test_push_graph_edge_entity(db_session):
    proj_id = _seed_project(db_session)
    svc = SyncService(db_session)

    request = SyncPushRequest(
        cursor=0,
        changes=[
            SyncChangeIn(
                entity_type="graph_edges",
                entity_id="ge-1",
                action="upsert",
                data={
                    "id": "ge-1",
                    "project_id": proj_id,
                    "from_node_id": "gn-1",
                    "to_node_id": "gn-2",
                    "relation_type": "ally",
                    "direction": "bidirectional",
                },
                local_version=1,
            )
        ],
    )
    result = svc.push(proj_id, "user-1", request)
    assert len(result.accepted) == 1

    pull = svc.pull(proj_id, "user-1", cursor=0)
    assert len(pull.changes) == 1
    assert pull.changes[0].entity_type == "graph_edges"
    assert pull.changes[0].data["from_node_id"] == "gn-1"


def test_push_timeline_edge_entity(db_session):
    proj_id = _seed_project(db_session)
    svc = SyncService(db_session)

    request = SyncPushRequest(
        cursor=0,
        changes=[
            SyncChangeIn(
                entity_type="timeline_edges",
                entity_id="te-1",
                action="upsert",
                data={
                    "id": "te-1",
                    "project_id": proj_id,
                    "from_event_id": "ev-1",
                    "to_event_id": "ev-2",
                    "edge_type": "causal",
                    "temporal_relation": "after",
                },
                local_version=1,
            )
        ],
    )
    result = svc.push(proj_id, "user-1", request)
    assert len(result.accepted) == 1

    pull = svc.pull(proj_id, "user-1", cursor=0)
    assert len(pull.changes) == 1
    assert pull.changes[0].entity_type == "timeline_edges"
    assert pull.changes[0].data["edge_type"] == "causal"


def test_push_all_l2_l3_entity_types_accepted(db_session):
    """All 24 P0/P1 entity types should be accepted."""
    from app.services.sync_service import ALLOWED_ENTITY_TYPES

    assert len(ALLOWED_ENTITY_TYPES) == 24
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
    assert ALLOWED_ENTITY_TYPES == expected
