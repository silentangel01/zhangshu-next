"""Tests for admin announcement management API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, utc_now
from tests.conftest import register_user, auth_headers


def _make_admin(db_session: Session, email: str = "admin@example.com") -> str:
    """Register an admin user directly in DB. Returns access token."""
    from app.core.security import hash_password
    from uuid import uuid4

    user = User(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password("securepassword123"),
        display_name="Admin",
        is_active=True,
        is_admin=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()

    from app.services.token_service import create_admin_access_token
    token = create_admin_access_token(user.id)
    return token


class TestAdminAnnouncements:
    def test_non_admin_rejected(self, client: TestClient, db_session: Session):
        # Create a non-admin user with admin_access token type so it passes
        # token validation but fails the admin check (403, not 401).
        from app.core.security import hash_password
        from app.services.token_service import create_admin_access_token
        from uuid import uuid4

        user = User(
            id=str(uuid4()),
            email="normal@example.com",
            password_hash=hash_password("securepassword123"),
            display_name="Normal",
            is_active=True,
            is_admin=False,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(user)
        db_session.commit()
        headers = auth_headers(create_admin_access_token(user.id))
        response = client.get("/api/admin/announcements", headers=headers)
        assert response.status_code == 403

    def test_admin_can_create_announcement(
        self, client: TestClient, db_session: Session
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)

        response = client.post(
            "/api/admin/announcements",
            headers=headers,
            json={
                "title": "测试公告",
                "body": "这是一条管理员公告。",
                "severity": "warning",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "测试公告"
        assert data["status"] == "draft"

    def test_admin_can_publish(
        self, client: TestClient, db_session: Session
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)

        # Create draft
        create_resp = client.post(
            "/api/admin/announcements",
            headers=headers,
            json={"title": "发布测试", "body": "正文内容"},
        )
        ann_id = create_resp.json()["id"]

        # Publish
        pub_resp = client.post(
            f"/api/admin/announcements/{ann_id}/publish",
            headers=headers,
        )
        assert pub_resp.status_code == 200
        assert pub_resp.json()["status"] == "published"

    def test_admin_can_archive(
        self, client: TestClient, db_session: Session
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)

        create_resp = client.post(
            "/api/admin/announcements",
            headers=headers,
            json={"title": "归档测试", "body": "正文内容"},
        )
        ann_id = create_resp.json()["id"]

        archive_resp = client.post(
            f"/api/admin/announcements/{ann_id}/archive",
            headers=headers,
        )
        assert archive_resp.status_code == 200
        assert archive_resp.json()["status"] == "archived"

    def test_admin_can_delete(
        self, client: TestClient, db_session: Session
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)

        create_resp = client.post(
            "/api/admin/announcements",
            headers=headers,
            json={"title": "删除测试", "body": "正文内容"},
        )
        ann_id = create_resp.json()["id"]

        del_resp = client.delete(
            f"/api/admin/announcements/{ann_id}",
            headers=headers,
        )
        assert del_resp.status_code == 204

    def test_reject_html_in_body(
        self, client: TestClient, db_session: Session
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)

        response = client.post(
            "/api/admin/announcements",
            headers=headers,
            json={
                "title": "XSS 测试",
                "body": "<script>alert('xss')</script>",
            },
        )
        assert response.status_code == 400

    def test_no_auth_rejected(self, client: TestClient):
        response = client.get("/api/admin/announcements")
        assert response.status_code == 401

    def test_admin_list_announcements(
        self, client: TestClient, db_session: Session
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)

        # Create two announcements
        client.post(
            "/api/admin/announcements",
            headers=headers,
            json={"title": "公告1", "body": "内容1"},
        )
        client.post(
            "/api/admin/announcements",
            headers=headers,
            json={"title": "公告2", "body": "内容2"},
        )

        response = client.get("/api/admin/announcements", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
