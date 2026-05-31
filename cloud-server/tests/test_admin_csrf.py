"""Tests for admin CSRF / Origin protection middleware."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DATABASE_URL"] = "sqlite:///./test_csrf.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-min-32-bytes"
os.environ["OSS_ACCESS_KEY_ID"] = "test-key-id"
os.environ["OSS_ACCESS_KEY_SECRET"] = "test-key-secret"
os.environ["OSS_BUCKET_NAME"] = "test-bucket"
os.environ["OSS_ENDPOINT"] = "oss-cn-hangzhou.aliyuncs.com"
# CSRF tests need origin checking enabled — conftest sets it to false globally
os.environ["ADMIN_REQUIRE_ORIGIN_CHECK"] = "true"

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
from app.core.config import get_settings  # noqa: E402
from app.services.token_service import create_admin_access_token  # noqa: E402
from app.models.user import User, utc_now  # noqa: E402
from app.core.security import hash_password  # noqa: E402

from uuid import uuid4  # noqa: E402


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


@pytest.fixture(autouse=True)
def _enable_csrf():
    """Enable CSRF origin checking for these tests (conftest disables it globally)."""
    from app.main import settings as _s
    old = _s.admin_require_origin_check
    _s.admin_require_origin_check = True
    yield
    _s.admin_require_origin_check = old


def _make_admin(db_session: Session, email: str = "csrf-admin@example.com") -> str:
    user = User(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password("securepassword123"),
        display_name="CSRF Admin",
        is_active=True,
        is_admin=True,
        admin_role="owner",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return create_admin_access_token(user.id)


class TestAdminCSRF:
    """Test CSRF protection for admin write endpoints."""

    def test_admin_get_no_csrf_required(self, client: TestClient, db_session: Session):
        """GET requests to admin endpoints should not require CSRF headers."""
        token = _make_admin(db_session)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/admin/dashboard/summary", headers=headers)
        assert resp.status_code == 200

    def test_admin_post_missing_custom_header(self, client: TestClient, db_session: Session):
        """POST without X-Zhangshu-Admin-Request should be rejected."""
        token = _make_admin(db_session)
        headers = {
            "Authorization": f"Bearer {token}",
            "Origin": "https://admin.example.com",
        }
        resp = client.post(
            "/api/admin/announcements",
            json={"title": "test", "body": "test body"},
            headers=headers,
        )
        assert resp.status_code == 403
        assert "安全验证" in resp.json()["detail"] or "header" in resp.json()["detail"]

    def test_admin_post_with_custom_header_passes(self, client: TestClient, db_session: Session):
        """POST with correct custom header should pass CSRF check."""
        token = _make_admin(db_session)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Zhangshu-Admin-Request": "1",
        }
        resp = client.post(
            "/api/admin/announcements",
            json={"title": "test", "body": "test body"},
            headers=headers,
        )
        # Should get past CSRF check (may succeed or fail on other validation)
        assert resp.status_code != 403 or "安全验证" not in resp.json().get("detail", "")

    def test_admin_post_wrong_custom_header(self, client: TestClient, db_session: Session):
        """POST with wrong custom header value should be rejected."""
        token = _make_admin(db_session)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Zhangshu-Admin-Request": "wrong",
        }
        resp = client.post(
            "/api/admin/announcements",
            json={"title": "test", "body": "test body"},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_non_admin_path_not_affected(self, client: TestClient, db_session: Session):
        """Non-admin paths should not be subject to CSRF checks."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_admin_delete_missing_custom_header(self, client: TestClient, db_session: Session):
        """DELETE without custom header should be rejected."""
        token = _make_admin(db_session)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.delete(
            "/api/admin/announcements/fake-id",
            headers=headers,
        )
        assert resp.status_code == 403
