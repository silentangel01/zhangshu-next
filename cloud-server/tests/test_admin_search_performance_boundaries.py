"""Tests for admin search validation boundaries and privacy.

Covers:
- Single-character keyword is rejected (400).
- Each entity type returns at most 10 results.
- Users without ``users:sensitive_view`` see masked emails.
- Feedback description is never returned in search results.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.announcement import Announcement  # noqa: E402
from app.models.feedback_ticket import FeedbackTicket  # noqa: E402
from app.models.user import User, utc_now  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.services.token_service import create_admin_access_token  # noqa: E402
from tests.conftest import auth_headers  # noqa: E402


def _make_admin(
    db_session: Session,
    email: str = "search-admin@example.com",
    admin_role: str = "owner",
) -> str:
    user = User(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password("securepassword123"),
        display_name="Search Admin",
        is_active=True,
        is_admin=True,
        admin_role=admin_role,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return create_admin_access_token(user.id)


def _make_support_admin(db_session: Session) -> str:
    """Support role does NOT have ``users:sensitive_view``."""
    user = User(
        id=str(uuid4()),
        email="support@example.com",
        password_hash=hash_password("securepassword123"),
        display_name="Support Admin",
        is_active=True,
        is_admin=False,
        admin_role="support",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return create_admin_access_token(user.id)


class TestAdminSearchBoundaries:
    def test_single_char_keyword_rejected(self, client: TestClient, db_session: Session):
        token = _make_admin(db_session)
        resp = client.get(
            "/api/admin/search?q=a", headers=auth_headers(token)
        )
        assert resp.status_code == 400

    def test_max_10_per_type(self, client: TestClient, db_session: Session):
        token = _make_admin(db_session)
        # Create 15 users with matching email
        for i in range(15):
            db_session.add(
                User(
                    id=str(uuid4()),
                    email=f"match-{i:02d}@example.com",
                    password_hash=hash_password("pw"),
                    display_name=f"Match User {i:02d}",
                    is_active=True,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        # 15 feedback tickets
        for i in range(15):
            db_session.add(
                FeedbackTicket(
                    id=str(uuid4()),
                    user_id=None,
                    title=f"match ticket {i:02d}",
                    description="desc",
                    status="open",
                    category="bug",
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        # 15 announcements
        for i in range(15):
            db_session.add(
                Announcement(
                    id=str(uuid4()),
                    title=f"match announcement {i:02d}",
                    body="body",
                    severity="info",
                    status="published",
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        db_session.commit()

        resp = client.get(
            "/api/admin/search?q=match", headers=auth_headers(token)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["users"]) == 10
        assert len(body["feedback"]) == 10
        assert len(body["announcements"]) == 10

    def test_support_role_email_masked(self, client: TestClient, db_session: Session):
        """Support role does not have ``users:sensitive_view``."""
        token = _make_support_admin(db_session)
        db_session.add(
            User(
                id=str(uuid4()),
                email="johndoe@example.com",
                password_hash=hash_password("pw"),
                display_name="John Doe",
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        db_session.commit()

        resp = client.get(
            "/api/admin/search?q=john", headers=auth_headers(token)
        )
        assert resp.status_code == 200
        users = resp.json()["users"]
        assert len(users) == 1
        assert users[0]["email"] == "j***@example.com"

    def test_owner_role_sees_full_email(self, client: TestClient, db_session: Session):
        token = _make_admin(db_session)  # owner
        db_session.add(
            User(
                id=str(uuid4()),
                email="janedoe@example.com",
                password_hash=hash_password("pw"),
                display_name="Jane Doe",
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        db_session.commit()

        resp = client.get(
            "/api/admin/search?q=jane", headers=auth_headers(token)
        )
        assert resp.status_code == 200
        users = resp.json()["users"]
        assert len(users) == 1
        assert users[0]["email"] == "janedoe@example.com"

    def test_feedback_description_not_returned(
        self, client: TestClient, db_session: Session
    ):
        token = _make_admin(db_session)
        db_session.add(
            FeedbackTicket(
                id=str(uuid4()),
                user_id=None,
                title="unique title",
                description="very secret description",
                status="open",
                category="bug",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        db_session.commit()

        # Search matching the description — result should not include it
        resp = client.get(
            "/api/admin/search?q=secret", headers=auth_headers(token)
        )
        assert resp.status_code == 200
        feedback = resp.json()["feedback"]
        assert len(feedback) == 1
        assert "description" not in feedback[0]
        # Search matching title returns same shape
        resp2 = client.get(
            "/api/admin/search?q=unique", headers=auth_headers(token)
        )
        body2 = resp2.json()
        assert body2["feedback"][0]["title"] == "unique title"
        assert "description" not in body2["feedback"][0]
