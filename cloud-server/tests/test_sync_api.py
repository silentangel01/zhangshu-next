"""Tests for the incremental sync API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import auth_headers, register_user


def _create_cloud_project(client: TestClient, headers: dict) -> str:
    resp = client.post("/api/projects", json={"title": "测试项目"}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ── Auth ─────────────────────────────────────────────────────────


def test_push_requires_auth(client: TestClient):
    resp = client.post(
        "/api/projects/fake-id/sync/push",
        json={"cursor": 0, "changes": []},
    )
    assert resp.status_code == 401


def test_pull_requires_auth(client: TestClient):
    resp = client.get("/api/projects/fake-id/sync/pull")
    assert resp.status_code == 401


# ── Project ownership isolation ──────────────────────────────────


def test_user_a_cannot_push_to_user_b_project(client: TestClient):
    # User A creates a project
    reg_a = register_user(client, email="a@example.com", password="securepassword123")
    headers_a = auth_headers(reg_a["access_token"])
    proj_id = _create_cloud_project(client, headers_a)

    # User B tries to push
    reg_b = register_user(client, email="b@example.com", password="securepassword123")
    headers_b = auth_headers(reg_b["access_token"])
    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-1",
                    "action": "upsert",
                    "data": {"id": "chap-1", "title": "第一章"},
                }
            ],
        },
        headers=headers_b,
    )
    assert resp.status_code == 400
    assert "无权" in resp.json()["detail"]


def test_user_a_cannot_pull_from_user_b_project(client: TestClient):
    reg_a = register_user(client, email="a@example.com", password="securepassword123")
    headers_a = auth_headers(reg_a["access_token"])
    proj_id = _create_cloud_project(client, headers_a)

    reg_b = register_user(client, email="b@example.com", password="securepassword123")
    headers_b = auth_headers(reg_b["access_token"])
    resp = client.get(
        f"/api/projects/{proj_id}/sync/pull?cursor=0",
        headers=headers_b,
    )
    assert resp.status_code == 400


# ── Push + Pull round-trip ───────────────────────────────────────


def test_push_and_pull_round_trip(client: TestClient):
    reg = register_user(client, password="securepassword123")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    # Push a new chapter
    push_resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-1",
                    "action": "upsert",
                    "data": {
                        "id": "chap-1",
                        "project_id": proj_id,
                        "title": "第一章",
                        "content": "正文内容",
                    },
                    "local_version": 1,
                    "local_updated_at": "2026-05-30T10:00:00+00:00",
                    "device_id": "device-a",
                }
            ],
        },
        headers=headers,
    )
    assert push_resp.status_code == 200
    push_data = push_resp.json()
    assert len(push_data["accepted"]) == 1
    assert push_data["accepted"][0]["entity_id"] == "chap-1"
    assert push_data["new_cursor"] > 0
    cursor = push_data["new_cursor"]

    # Pull from cursor 0 should return the change
    pull_resp = client.get(
        f"/api/projects/{proj_id}/sync/pull?cursor=0",
        headers=headers,
    )
    assert pull_resp.status_code == 200
    pull_data = pull_resp.json()
    assert len(pull_data["changes"]) == 1
    assert pull_data["changes"][0]["entity_type"] == "chapters"
    assert pull_data["changes"][0]["entity_id"] == "chap-1"
    assert pull_data["changes"][0]["data"]["title"] == "第一章"
    assert pull_data["new_cursor"] == cursor

    # Pull from current cursor should return nothing
    pull_resp2 = client.get(
        f"/api/projects/{proj_id}/sync/pull?cursor={cursor}",
        headers=headers,
    )
    assert pull_resp2.status_code == 200
    assert len(pull_resp2.json()["changes"]) == 0


def test_push_multiple_entities(client: TestClient):
    reg = register_user(client, password="securepassword123")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "projects",
                    "entity_id": "proj-1",
                    "action": "upsert",
                    "data": {"id": "proj-1", "title": "我的小说"},
                },
                {
                    "entity_type": "volumes",
                    "entity_id": "vol-1",
                    "action": "upsert",
                    "data": {"id": "vol-1", "project_id": "proj-1", "title": "第一卷"},
                },
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-1",
                    "action": "upsert",
                    "data": {"id": "chap-1", "title": "第一章"},
                },
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["accepted"]) == 3


# ── Entity type whitelist ────────────────────────────────────────


def test_push_rejects_unknown_entity_type(client: TestClient):
    reg = register_user(client, password="securepassword123")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "knowledge_items",
                    "entity_id": "ki-1",
                    "action": "upsert",
                    "data": {"id": "ki-1", "title": "未知知识"},
                }
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rejected"]) == 1
    assert "不支持的实体类型" in data["rejected"][0]["reason"]


# ── Cursor is change id, not timestamp ───────────────────────────


def test_cursor_is_change_id(client: TestClient):
    reg = register_user(client, password="securepassword123")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    # Push first change
    resp1 = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-1",
                    "action": "upsert",
                    "data": {"id": "chap-1", "title": "第一章"},
                }
            ],
        },
        headers=headers,
    )
    cursor1 = resp1.json()["new_cursor"]

    # Push second change
    resp2 = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": cursor1,
            "changes": [
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-2",
                    "action": "upsert",
                    "data": {"id": "chap-2", "title": "第二章"},
                }
            ],
        },
        headers=headers,
    )
    cursor2 = resp2.json()["new_cursor"]

    # Cursor must be monotonically increasing integer
    assert cursor2 > cursor1

    # Pull from cursor1 should only return the second change
    pull = client.get(
        f"/api/projects/{proj_id}/sync/pull?cursor={cursor1}",
        headers=headers,
    )
    changes = pull.json()["changes"]
    assert len(changes) == 1
    assert changes[0]["entity_id"] == "chap-2"


# ── Snapshot creation ────────────────────────────────────────────


def test_push_creates_snapshots(client: TestClient):
    reg = register_user(client, password="securepassword123")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    # Push initial version
    client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-1",
                    "action": "upsert",
                    "data": {"id": "chap-1", "title": "第一章 v1"},
                }
            ],
        },
        headers=headers,
    )

    # Push updated version
    client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 1,
            "changes": [
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-1",
                    "action": "upsert",
                    "data": {"id": "chap-1", "title": "第一章 v2"},
                    "base_cloud_version": 1,
                }
            ],
        },
        headers=headers,
    )

    # List snapshots
    snap_resp = client.get(
        f"/api/projects/{proj_id}/sync/snapshots"
        "?entity_type=chapters&entity_id=chap-1",
        headers=headers,
    )
    assert snap_resp.status_code == 200
    snapshots = snap_resp.json()
    assert len(snapshots) >= 2


# ── Conflict recording ───────────────────────────────────────────


def test_conflict_preserves_loser_payload(client: TestClient):
    reg = register_user(client, password="securepassword123")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    # Device A pushes v1
    client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-1",
                    "action": "upsert",
                    "data": {"id": "chap-1", "title": "原始版本"},
                    "device_id": "device-a",
                    "local_updated_at": "2026-05-30T10:00:00+00:00",
                }
            ],
        },
        headers=headers,
    )

    # Device B pushes v2 with base_cloud_version=0 (stale)
    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-1",
                    "action": "upsert",
                    "data": {"id": "chap-1", "title": "设备B修改"},
                    "base_cloud_version": 0,
                    "device_id": "device-b",
                    "local_updated_at": "2026-05-30T09:00:00+00:00",
                }
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Device B's update is older, so cloud wins
    # The change should be recorded as a conflict
    assert len(data["conflicts"]) >= 1 or len(data["accepted"]) >= 1

    # Verify conflict was recorded
    conflict_resp = client.get(
        f"/api/projects/{proj_id}/sync/conflicts?resolved=false",
        headers=headers,
    )
    assert conflict_resp.status_code == 200
    conflicts = conflict_resp.json()
    assert len(conflicts) >= 1
    # Loser payload should be preserved (not empty)
    assert conflicts[0]["loser_payload_json"] is not None


# ── Payload / limit enforcement ──────────────────────────────────


def test_push_too_many_changes(client: TestClient):
    reg = register_user(client, password="securepassword123")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    # 201 changes exceeds the default limit of 200
    changes = [
        {
            "entity_type": "chapters",
            "entity_id": f"chap-{i}",
            "action": "upsert",
            "data": {"id": f"chap-{i}", "title": f"第{i}章"},
        }
        for i in range(201)
    ]
    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={"cursor": 0, "changes": changes},
        headers=headers,
    )
    assert resp.status_code == 400


# ── Delete action ────────────────────────────────────────────────


def test_push_delete_action(client: TestClient):
    reg = register_user(client, password="securepassword123")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    # First upsert
    client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-1",
                    "action": "upsert",
                    "data": {"id": "chap-1", "title": "第一章"},
                }
            ],
        },
        headers=headers,
    )

    # Then delete
    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 1,
            "changes": [
                {
                    "entity_type": "chapters",
                    "entity_id": "chap-1",
                    "action": "delete",
                    "data": {"id": "chap-1", "title": "第一章", "deleted_at": "2026-05-30T12:00:00+00:00"},
                    "base_cloud_version": 1,
                }
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["accepted"]) == 1

    # Pull should show the delete action
    pull = client.get(
        f"/api/projects/{proj_id}/sync/pull?cursor=0",
        headers=headers,
    )
    changes = pull.json()["changes"]
    delete_changes = [c for c in changes if c["action"] == "delete"]
    assert len(delete_changes) == 1


# ── L2 P0 entity push/pull ──────────────────────────────────────


def test_push_and_pull_characters(client: TestClient):
    reg = register_user(client, password="securepassword123")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "characters",
                    "entity_id": "char-1",
                    "action": "upsert",
                    "data": {
                        "id": "char-1",
                        "project_id": proj_id,
                        "name": "主角",
                        "role": "protagonist",
                        "importance": "major",
                        "status": "active",
                        "summary": "故事的主角",
                    },
                    "local_version": 1,
                    "local_updated_at": "2026-05-30T10:00:00+00:00",
                    "device_id": "device-a",
                }
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["accepted"]) == 1
    assert data["accepted"][0]["entity_type"] == "characters"

    pull = client.get(
        f"/api/projects/{proj_id}/sync/pull?cursor=0",
        headers=headers,
    )
    assert pull.status_code == 200
    changes = pull.json()["changes"]
    assert len(changes) == 1
    assert changes[0]["entity_type"] == "characters"
    assert changes[0]["data"]["name"] == "主角"


def test_push_and_pull_graph_nodes(client: TestClient):
    reg = register_user(client, password="securepassword123")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "graph_nodes",
                    "entity_id": "gn-1",
                    "action": "upsert",
                    "data": {
                        "id": "gn-1",
                        "project_id": proj_id,
                        "title": "节点A",
                        "node_type": "character",
                        "bound_type": "character",
                        "bound_id": "char-1",
                        "x": 100.0,
                        "y": 200.0,
                    },
                    "local_version": 1,
                    "local_updated_at": "2026-05-30T10:00:00+00:00",
                    "device_id": "device-a",
                },
                {
                    "entity_type": "graph_edges",
                    "entity_id": "ge-1",
                    "action": "upsert",
                    "data": {
                        "id": "ge-1",
                        "project_id": proj_id,
                        "from_node_id": "gn-1",
                        "to_node_id": "gn-2",
                        "relation_type": "ally",
                        "direction": "bidirectional",
                    },
                    "local_version": 1,
                    "local_updated_at": "2026-05-30T10:00:00+00:00",
                    "device_id": "device-a",
                },
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["accepted"]) == 2

    pull = client.get(
        f"/api/projects/{proj_id}/sync/pull?cursor=0",
        headers=headers,
    )
    assert pull.status_code == 200
    changes = pull.json()["changes"]
    assert len(changes) == 2
    entity_types = {c["entity_type"] for c in changes}
    assert "graph_nodes" in entity_types
    assert "graph_edges" in entity_types


# ── L3 P1 join entity push/pull ────────────────────────────────


def test_l3_push_pull_chapter_characters(client: TestClient):
    """P1 chapter_characters should be accepted for push and pull."""
    reg = register_user(client, "l3user1@test.com", "pass12345678")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "chapter_characters",
                    "entity_id": "cc-1",
                    "action": "upsert",
                    "data": {
                        "id": "cc-1",
                        "project_id": proj_id,
                        "chapter_id": "ch-1",
                        "character_id": "char-1",
                        "relation_type": "appears",
                        "note": "",
                    },
                    "local_version": 1,
                    "local_updated_at": "2026-05-30T10:00:00+00:00",
                    "device_id": "device-a",
                },
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["accepted"]) == 1

    pull = client.get(
        f"/api/projects/{proj_id}/sync/pull?cursor=0",
        headers=headers,
    )
    assert pull.status_code == 200
    changes = pull.json()["changes"]
    assert len(changes) == 1
    assert changes[0]["entity_type"] == "chapter_characters"


def test_l3_push_pull_outline_item_timeline_events(client: TestClient):
    """P1 material link entity should be accepted for push and pull."""
    reg = register_user(client, "l3user2@test.com", "pass12345678")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "outline_item_timeline_events",
                    "entity_id": "oite-1",
                    "action": "upsert",
                    "data": {
                        "id": "oite-1",
                        "project_id": proj_id,
                        "outline_item_id": "oi-1",
                        "timeline_event_id": "ev-1",
                        "relation_type": "related",
                        "note": "",
                    },
                    "local_version": 1,
                    "local_updated_at": "2026-05-30T10:00:00+00:00",
                    "device_id": "device-a",
                },
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["accepted"]) == 1

    pull = client.get(
        f"/api/projects/{proj_id}/sync/pull?cursor=0",
        headers=headers,
    )
    assert pull.status_code == 200
    changes = pull.json()["changes"]
    assert len(changes) == 1
    assert changes[0]["entity_type"] == "outline_item_timeline_events"


def test_l3_rejects_non_whitelisted_type(client: TestClient):
    """P2/non-whitelisted entity types should still be rejected."""
    reg = register_user(client, "l3user3@test.com", "pass12345678")
    headers = auth_headers(reg["access_token"])
    proj_id = _create_cloud_project(client, headers)

    resp = client.post(
        f"/api/projects/{proj_id}/sync/push",
        json={
            "cursor": 0,
            "changes": [
                {
                    "entity_type": "knowledge_items",
                    "entity_id": "ki-1",
                    "action": "upsert",
                    "data": {"id": "ki-1", "title": "知识"},
                    "local_version": 1,
                    "local_updated_at": "2026-05-30T10:00:00+00:00",
                    "device_id": "device-a",
                },
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rejected"]) == 1
    assert "knowledge_items" in data["rejected"][0]["reason"]
