"""Tests for token invalidation — password change and refresh replay detection."""

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

os.environ["DATABASE_URL"] = "sqlite:///./test_token_inv.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-min-32-bytes"
os.environ["OSS_ACCESS_KEY_ID"] = "test-key-id"
os.environ["OSS_ACCESS_KEY_SECRET"] = "test-key-secret"
os.environ["OSS_BUCKET_NAME"] = "test-bucket"
os.environ["OSS_ENDPOINT"] = "oss-cn-hangzhou.aliyuncs.com"

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
from app.models.user import User, utc_now  # noqa: E402
from app.models.refresh_token import RefreshToken  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.services.token_service import (  # noqa: E402
    create_access_token,
    create_refresh_token,
    hash_jti,
)
from tests.conftest import auth_headers, register_user  # noqa: E402


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


class TestPasswordChangeTokenInvalidation:
    """After password change, old access tokens should be rejected."""

    def test_old_access_token_rejected_after_password_change(
        self, client: TestClient, db_session: Session
    ):
        """Token issued before password change should be invalid."""
        # Register and get access token
        data = register_user(client, email="pwduser@example.com")
        old_token = data["access_token"]

        # Get user and update password_changed_at to simulate password change
        user = db_session.query(User).filter_by(email="pwduser@example.com").first()
        assert user is not None

        # Set password_changed_at to "now" — the token was issued before this
        from datetime import timedelta
        user.password_changed_at = utc_now() + timedelta(seconds=1)
        db_session.commit()

        # Old token should be rejected
        headers = auth_headers(old_token)
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_new_access_token_works_after_password_change(
        self, client: TestClient, db_session: Session
    ):
        """Token issued after password change should work."""
        data = register_user(client, email="pwduser2@example.com")

        # Sleep to ensure password change happens in a different second
        # than the original token issuance (JWT iat has second precision)
        import time
        time.sleep(1.1)

        # Change password via API
        headers = auth_headers(data["access_token"])
        resp = client.post(
            "/api/account/password/change",
            json={
                "old_password": "securepassword123",
                "new_password": "NewSecure456!",
            },
            headers=headers,
        )
        assert resp.status_code == 200

        # Old token should be rejected
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

        # Sleep to ensure new login token is in a later second
        time.sleep(1.1)

        # Login again with new password
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "pwduser2@example.com", "password": "NewSecure456!"},
        )
        assert login_resp.status_code == 200
        new_token = login_resp.json()["access_token"]

        # New token should work
        resp = client.get("/api/auth/me", headers=auth_headers(new_token))
        assert resp.status_code == 200


class TestRefreshTokenReplayDetection:
    """Reusing a rotated refresh token should revoke all sessions."""

    def test_replay_revokes_all_sessions(
        self, client: TestClient, db_session: Session
    ):
        """Replaying an old refresh token should revoke all active tokens."""
        data = register_user(client, email="replay@example.com")
        old_refresh = data["refresh_token"]

        # Use the refresh token to get new tokens (this rotates the old one)
        resp = client.post(
            "/api/auth/refresh",
            headers=auth_headers(data["access_token"]),
            json={"refresh_token": old_refresh},
        )
        assert resp.status_code == 200
        # The old refresh token is now rotated (replaced_by_id is set)

        # Now try to replay the old refresh token
        resp = client.post(
            "/api/auth/refresh",
            headers=auth_headers(resp.json()["access_token"]),
            json={"refresh_token": old_refresh},
        )
        # Should be rejected
        assert resp.status_code == 401

        # All refresh tokens for this user should now be revoked
        user = db_session.query(User).filter_by(email="replay@example.com").first()
        active_tokens = (
            db_session.query(RefreshToken)
            .filter_by(user_id=user.id, revoked_at=None)
            .count()
        )
        assert active_tokens == 0
