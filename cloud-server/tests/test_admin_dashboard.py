"""Tests for admin dashboard API — summary, activity, feedback-stats."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, utc_now
from app.services.token_service import create_access_token, create_admin_access_token
from tests.conftest import auth_headers, register_user


def _make_admin(db_session: Session, email: str = "dash-admin@example.com") -> str:
    user = User(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password("securepassword123"),
        display_name="Dash Admin",
        is_active=True,
        is_admin=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return create_admin_access_token(user.id)


class TestAdminDashboard:
    def test_no_auth_rejected(self, client: TestClient):
        response = client.get("/api/admin/dashboard/summary")
        assert response.status_code == 401

    def test_non_admin_rejected(self, client: TestClient, db_session: Session):
        # A regular access token (type "access") is rejected with 401
        # because the endpoint expects "admin_access" type.
        data = register_user(client, email="user@example.com")
        headers = auth_headers(data["access_token"])
        response = client.get("/api/admin/dashboard/summary", headers=headers)
        assert response.status_code == 401

    def test_get_summary(self, client: TestClient, db_session: Session):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        response = client.get("/api/admin/dashboard/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_24h" in data
        assert "today_registrations" in data

    def test_get_activity(self, client: TestClient, db_session: Session):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        response = client.get(
            "/api/admin/dashboard/activity?days=14", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "daily_active" in data
        assert isinstance(data["daily_active"], list)

    def test_get_feedback_stats(self, client: TestClient, db_session: Session):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        response = client.get("/api/admin/dashboard/feedback-stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "by_status" in data
        assert "by_category" in data
