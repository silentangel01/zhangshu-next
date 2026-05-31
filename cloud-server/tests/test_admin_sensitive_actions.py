"""Tests for high-risk admin actions — reason requirements, last-owner protection, role changes."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DATABASE_URL"] = "sqlite:///./test_sensitive.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-min-32-bytes"
os.environ["OSS_ACCESS_KEY_ID"] = "test-key-id"
os.environ["OSS_ACCESS_KEY_SECRET"] = "test-key-secret"
os.environ["OSS_BUCKET_NAME"] = "test-bucket"
os.environ["OSS_ENDPOINT"] = "oss-cn-hangzhou.aliyuncs.com"
os.environ["ADMIN_REQUIRE_ORIGIN_CHECK"] = "false"

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402

import app.models.user  # noqa: E402, F401
import app.models.refresh_token  # noqa: E402, F401
import app.models.cloud_project  # noqa: E402, F401
import app.models.cloud_backup  # noqa: E402, F401
import app.models.rate_limit_event  # noqa: E402, F401
import app.models.account_deletion_request  # noqa: E402, F401
import app.models.announcement  # noqa: E402, F401
import app.models.feedback_ticket  # noqa: E402, F401
import app.models.feedback_attachment  # noqa: E402, F401
import app.models.feedback_reply  # noqa: E402, F401
import app.models.user_activity_event  # noqa: E402, F401
import app.models.audit_log  # noqa: E402, F401

from app.main import app  # noqa: E402
from app.services.token_service import create_admin_access_token  # noqa: E402
from app.models.user import User, utc_now  # noqa: E402
from app.models.refresh_token import RefreshToken  # noqa: E402
from app.core.security import hash_password  # noqa: E402


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestSession()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _make_admin(
    db_session: Session,
    email: str = "sensitive-admin@example.com",
    admin_role: str | None = None,
    is_admin: bool = True,
) -> tuple[str, str]:
    """Create admin user and return (user_id, token)."""
    uid = str(uuid4())
    user = User(
        id=uid,
        email=email,
        password_hash=hash_password("securepassword123"),
        display_name="Sensitive Admin",
        is_active=True,
        is_admin=is_admin,
        admin_role=admin_role,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return uid, create_admin_access_token(uid)


def _make_user(
    db_session: Session,
    email: str = "regular-user@example.com",
    is_admin: bool = False,
) -> str:
    uid = str(uuid4())
    user = User(
        id=uid,
        email=email,
        password_hash=hash_password("securepassword123"),
        display_name="Regular User",
        is_active=True,
        is_admin=is_admin,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return uid


def _add_refresh_token(db_session: Session, user_id: str) -> str:
    """Add an active refresh token for a user."""
    tid = str(uuid4())
    from datetime import timedelta
    rt = RefreshToken(
        id=tid,
        user_id=user_id,
        jti_hash="test-jti-hash",
        expires_at=utc_now() + timedelta(hours=8),
        user_agent="test-agent",
        client_ip="127.0.0.1",
    )
    db_session.add(rt)
    db_session.commit()
    return tid


class TestToggleActive:
    """Tests for POST /api/admin/users/{id}/toggle-active."""

    def test_requires_reason(self, client: TestClient, db_session: Session):
        """Toggle without reason body should fail."""
        uid, token = _make_admin(db_session)
        target_id = _make_user(db_session)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            f"/api/admin/users/{target_id}/toggle-active",
            headers=headers,
        )
        assert resp.status_code == 422  # missing body

    def test_toggle_with_reason(self, client: TestClient, db_session: Session):
        """Toggle with valid reason should succeed."""
        uid, token = _make_admin(db_session)
        target_id = _make_user(db_session)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            f"/api/admin/users/{target_id}/toggle-active",
            json={"reason": "Spamming"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False

    def test_cannot_toggle_self(self, client: TestClient, db_session: Session):
        """Admin cannot toggle their own active status."""
        uid, token = _make_admin(db_session)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            f"/api/admin/users/{uid}/toggle-active",
            json={"reason": "Self test"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_last_owner_protection(self, client: TestClient, db_session: Session):
        """Cannot disable the last owner/admin."""
        uid, token = _make_admin(db_session)
        # This admin is the only admin in the DB
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            f"/api/admin/users/{uid}/toggle-active",
            json={"reason": "Test"},
            headers=headers,
        )
        # Should be 400 (self-toggle) before even hitting last-owner check
        assert resp.status_code == 400

    def test_disabling_user_revokes_refresh_tokens(
        self, client: TestClient, db_session: Session
    ):
        """Disabling a user should revoke their refresh tokens."""
        uid, token = _make_admin(db_session)
        target_id = _make_user(db_session, email="target@example.com")
        rt_id = _add_refresh_token(db_session, target_id)

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            f"/api/admin/users/{target_id}/toggle-active",
            json={"reason": "Account compromised"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        # Verify refresh token is revoked
        from sqlalchemy import select
        rt = db_session.get(RefreshToken, rt_id)
        assert rt is not None
        assert rt.revoked_at is not None


class TestForceLogout:
    """Tests for POST /api/admin/users/{id}/force-logout."""

    def test_requires_reason(self, client: TestClient, db_session: Session):
        """Force logout without reason body should fail."""
        uid, token = _make_admin(db_session)
        target_id = _make_user(db_session)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            f"/api/admin/users/{target_id}/force-logout",
            headers=headers,
        )
        assert resp.status_code == 422

    def test_force_logout_with_reason(self, client: TestClient, db_session: Session):
        """Force logout with reason should succeed."""
        uid, token = _make_admin(db_session)
        target_id = _make_user(db_session)
        _add_refresh_token(db_session, target_id)

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            f"/api/admin/users/{target_id}/force-logout",
            json={"reason": "Suspicious activity"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["tokens_revoked"] == 1


class TestAdminRoles:
    """Tests for the admin roles API."""

    def test_permissions_matrix(self, client: TestClient, db_session: Session):
        """GET /api/admin/roles/permissions should return the role matrix."""
        uid, token = _make_admin(db_session)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/admin/roles/permissions", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "roles" in data
        assert "owner" in data["roles"]
        assert "current_user_role" in data
        assert "current_user_permissions" in data
        # Bootstrap admin → owner
        assert data["current_user_role"] == "owner"

    def test_change_role_requires_confirm_text(
        self, client: TestClient, db_session: Session
    ):
        """Role change without correct confirm_text should fail."""
        uid, token = _make_admin(db_session)
        target_id = _make_user(db_session, email="target@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.patch(
            f"/api/admin/roles/users/{target_id}/admin-role",
            json={
                "admin_role": "support",
                "reason": "Promoting to support",
                "confirm_text": "wrong text",
            },
            headers=headers,
        )
        assert resp.status_code == 400

    def test_change_role_success(self, client: TestClient, db_session: Session):
        """Role change with correct confirm_text should succeed."""
        uid, token = _make_admin(db_session)
        target_id = _make_user(db_session, email="target@example.com")
        _add_refresh_token(db_session, target_id)

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.patch(
            f"/api/admin/roles/users/{target_id}/admin-role",
            json={
                "admin_role": "support",
                "reason": "New support team member",
                "confirm_text": "确认变更角色",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["admin_role"] == "support"
        assert data["effective_role"] == "support"

    def test_cannot_change_own_role(
        self, client: TestClient, db_session: Session
    ):
        """Admin cannot change their own role."""
        uid, token = _make_admin(db_session)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.patch(
            f"/api/admin/roles/users/{uid}/admin-role",
            json={
                "admin_role": "readonly",
                "reason": "Demoting self",
                "confirm_text": "确认变更角色",
            },
            headers=headers,
        )
        assert resp.status_code == 400

    def test_role_change_revokes_refresh_tokens(
        self, client: TestClient, db_session: Session
    ):
        """Changing a user's role should revoke their refresh tokens."""
        uid, token = _make_admin(db_session)
        target_id = _make_user(db_session, email="target@example.com")
        rt_id = _add_refresh_token(db_session, target_id)

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.patch(
            f"/api/admin/roles/users/{target_id}/admin-role",
            json={
                "admin_role": "ops",
                "reason": "Role change",
                "confirm_text": "确认变更角色",
            },
            headers=headers,
        )
        assert resp.status_code == 200

        rt = db_session.get(RefreshToken, rt_id)
        assert rt is not None
        assert rt.revoked_at is not None

    def test_non_owner_cannot_manage_roles(
        self, client: TestClient, db_session: Session
    ):
        """Non-owner admin cannot change roles."""
        # Create a support-level admin
        uid, token = _make_admin(
            db_session,
            email="support@example.com",
            admin_role="support",
            is_admin=False,
        )
        target_id = _make_user(db_session, email="target2@example.com")

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.patch(
            f"/api/admin/roles/users/{target_id}/admin-role",
            json={
                "admin_role": "ops",
                "reason": "Promotion",
                "confirm_text": "确认变更角色",
            },
            headers=headers,
        )
        assert resp.status_code == 403
