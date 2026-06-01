"""Tests for public announcements API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.announcement import Announcement
from app.models.user import utc_now
from tests.conftest import register_user, auth_headers


def _create_published_announcement(
    db_session: Session, title: str = "测试公告", severity: str = "info"
) -> Announcement:
    """Helper to create a published announcement directly in DB."""
    now = utc_now()
    a = Announcement(
        id="ann-001",
        title=title,
        body="这是一条测试公告正文。",
        severity=severity,
        status="published",
        audience="all",
        published_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(a)
    db_session.commit()
    return a


class TestListAnnouncements:
    def test_empty_when_no_announcements(self, client: TestClient):
        response = client.get("/api/announcements")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_published_announcements(
        self, client: TestClient, db_session: Session
    ):
        _create_published_announcement(db_session, "版本更新通知")
        response = client.get("/api/announcements")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "版本更新通知"

    def test_excludes_drafts(self, client: TestClient, db_session: Session):
        now = utc_now()
        a = Announcement(
            id="ann-draft",
            title="草稿",
            body="草稿内容",
            severity="info",
            status="draft",
            audience="all",
            created_at=now,
            updated_at=now,
        )
        db_session.add(a)
        db_session.commit()

        response = client.get("/api/announcements")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_excludes_expired(self, client: TestClient, db_session: Session):
        from datetime import timedelta

        now = utc_now()
        a = Announcement(
            id="ann-expired",
            title="已过期",
            body="已过期内容",
            severity="info",
            status="published",
            audience="all",
            published_at=now - timedelta(days=2),
            starts_at=now - timedelta(days=2),
            ends_at=now - timedelta(days=1),
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
        db_session.add(a)
        db_session.commit()

        response = client.get("/api/announcements")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_no_auth_required(self, client: TestClient, db_session: Session):
        _create_published_announcement(db_session)
        response = client.get("/api/announcements")
        assert response.status_code == 200

    def test_platform_filter(self, client: TestClient, db_session: Session):
        now = utc_now()
        a1 = Announcement(
            id="ann-win",
            title="Windows 专用",
            body="内容",
            severity="info",
            status="published",
            audience="all",
            platform="windows",
            published_at=now,
            created_at=now,
            updated_at=now,
        )
        a2 = Announcement(
            id="ann-all",
            title="全平台",
            body="内容",
            severity="info",
            status="published",
            audience="all",
            platform=None,
            published_at=now,
            created_at=now,
            updated_at=now,
        )
        db_session.add_all([a1, a2])
        db_session.commit()

        # Filter by windows → should get both (windows + null platform)
        response = client.get("/api/announcements?platform=windows")
        data = response.json()
        assert data["total"] == 2

        # Filter by macos → only the "all platforms" one
        response = client.get("/api/announcements?platform=macos")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "全平台"
