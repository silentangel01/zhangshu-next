"""Tests for admin feedback management API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.feedback_ticket import FeedbackTicket, utc_now
from app.models.user import User
from app.services.token_service import create_admin_access_token
from tests.conftest import auth_headers


def _make_admin(db_session: Session, email: str = "fb-admin@example.com") -> str:
    user = User(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password("securepassword123"),
        display_name="FB Admin",
        is_active=True,
        is_admin=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return create_admin_access_token(user.id)


def _create_feedback_ticket(db_session: Session, **kwargs) -> FeedbackTicket:
    now = utc_now()
    ticket = FeedbackTicket(
        id=kwargs.get("id", str(uuid4())),
        user_id=kwargs.get("user_id"),
        contact_email=kwargs.get("contact_email", "user@example.com"),
        category=kwargs.get("category", "bug"),
        title=kwargs.get("title", "测试反馈"),
        description=kwargs.get("description", "这是一条测试反馈描述，至少十个字符。"),
        status=kwargs.get("status", "open"),
        created_at=now,
        updated_at=now,
    )
    db_session.add(ticket)
    db_session.commit()
    return ticket


class TestAdminFeedback:
    def test_non_admin_rejected(self, client: TestClient, db_session: Session):
        # Create a non-admin user with admin_access token type so it passes
        # token validation but fails the admin check (403, not 401).
        from app.services.token_service import create_admin_access_token
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
        response = client.get("/api/admin/feedback", headers=headers)
        assert response.status_code == 403

    def test_admin_list_feedback(
        self, client: TestClient, db_session: Session, mock_oss
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        _create_feedback_ticket(db_session, title="反馈1")
        _create_feedback_ticket(db_session, title="反馈2")

        response = client.get("/api/admin/feedback", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_admin_get_feedback(
        self, client: TestClient, db_session: Session, mock_oss
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        ticket = _create_feedback_ticket(db_session, title="详细反馈")

        response = client.get(
            f"/api/admin/feedback/{ticket.id}", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["title"] == "详细反馈"

    def test_admin_update_status(
        self, client: TestClient, db_session: Session, mock_oss
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        ticket = _create_feedback_ticket(db_session)

        response = client.patch(
            f"/api/admin/feedback/{ticket.id}",
            headers=headers,
            json={"status": "triaged", "priority": "high"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "triaged"
        assert response.json()["priority"] == "high"

    def test_admin_delete_feedback(
        self, client: TestClient, db_session: Session, mock_oss
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        ticket = _create_feedback_ticket(db_session)

        response = client.delete(
            f"/api/admin/feedback/{ticket.id}", headers=headers
        )
        assert response.status_code == 204

    def test_admin_filter_by_category(
        self, client: TestClient, db_session: Session, mock_oss
    ):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        _create_feedback_ticket(db_session, category="bug")
        _create_feedback_ticket(db_session, category="suggestion")

        response = client.get(
            "/api/admin/feedback?category=bug", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "bug"

    def test_no_auth_rejected(self, client: TestClient):
        response = client.get("/api/admin/feedback")
        assert response.status_code == 401
