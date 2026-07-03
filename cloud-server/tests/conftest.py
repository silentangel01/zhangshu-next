"""Shared test fixtures."""

from __future__ import annotations

import os
import sys
from datetime import timedelta
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure the app package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Override settings before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test_cloud_server.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-min-32-bytes"
os.environ["OSS_ACCESS_KEY_ID"] = "test-key-id"
os.environ["OSS_ACCESS_KEY_SECRET"] = "test-key-secret"
os.environ["OSS_BUCKET_NAME"] = "test-bucket"
os.environ["OSS_ENDPOINT"] = "oss-cn-hangzhou.aliyuncs.com"
os.environ["ADMIN_REQUIRE_ORIGIN_CHECK"] = "false"
os.environ["EMAIL_DELIVERY_MODE"] = "log"
os.environ["AUTH_EMAIL_CODE_SECRET"] = "test-email-code-secret"
os.environ["PHONE_AUTH_ENABLED"] = "true"
os.environ["SMS_DELIVERY_MODE"] = "log"
os.environ["AUTH_PHONE_CODE_SECRET"] = "test-phone-code-secret"

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402

# Import all models BEFORE importing app — `import app.models.X` rebinds
# the name `app` to the package module, shadowing the FastAPI instance.
import app.models.user  # noqa: E402, F401
import app.models.refresh_token  # noqa: E402, F401
import app.models.email_verification_code  # noqa: E402, F401
import app.models.phone_verification_code  # noqa: E402, F401
import app.models.auth_identity  # noqa: E402, F401
import app.models.oauth_login_session  # noqa: E402, F401
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
import app.models.admin_metric_snapshot  # noqa: E402, F401
import app.models.cloud_sync_entity  # noqa: E402, F401
import app.models.cloud_sync_change  # noqa: E402, F401
import app.models.cloud_sync_snapshot  # noqa: E402, F401
import app.models.cloud_sync_conflict  # noqa: E402, F401

from app.main import app  # noqa: E402 — must come AFTER model imports
from app.core.security import normalize_email  # noqa: E402
from app.core.security import normalize_phone_number  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.models.email_verification_code import EmailVerificationCode  # noqa: E402
from app.models.phone_verification_code import PhoneVerificationCode  # noqa: E402
from app.models.user import utc_now  # noqa: E402
from app.services.email_verification_service import hash_email_code  # noqa: E402
from app.services.phone_verification_service import hash_phone_code  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    """Clean up DB rate limit events after each test."""
    yield
    # DB rate limit table is recreated each test via create_all,
    # so no explicit cleanup needed.


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
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


@pytest.fixture
def mock_oss():
    """Return a mock OSSStorage that can be patched into BackupService."""
    oss = MagicMock()
    oss.is_configured = True
    oss.build_object_key.return_value = "backups/user/proj/backup/file.zip"
    oss.generate_put_url.return_value = "https://oss.example.com/presigned-put"
    oss.generate_get_url.return_value = "https://oss.example.com/presigned-get"
    oss.head_object.return_value = {"size": 100, "content_type": "application/zip"}
    oss.delete_object.return_value = None
    return oss


@pytest.fixture
def client(db_session: Session, mock_oss) -> Generator[TestClient, None, None]:
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # Patch OSSStorage so BackupService uses mock
    with patch("app.services.backup_service.OSSStorage", return_value=mock_oss):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    app.dependency_overrides.clear()


def register_user(
    client: TestClient,
    email: str = "test@example.com",
    password: str = "securepassword123",
    display_name: str = "Test User",
) -> dict:
    verification_code = seed_email_verification_code(client, email, "register")
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "verification_code": verification_code,
        },
    )
    return response.json()


def seed_email_verification_code(
    client: TestClient,
    email: str,
    purpose: str,
    code: str = "123456",
) -> str:
    override = app.dependency_overrides.get(get_db)
    if override is None:
        raise RuntimeError("get_db override is not configured for test client")

    db = next(override())
    settings = get_settings()
    normalized = normalize_email(email)
    now = utc_now()
    db.add(
        EmailVerificationCode(
            id=str(uuid4()),
            email=normalized,
            purpose=purpose,
            code_hash=hash_email_code(
                normalized,
                purpose,
                code,
                settings.auth_email_code_secret or settings.jwt_secret_key,
            ),
            expires_at=now + timedelta(minutes=10),
            attempt_count=0,
            max_attempts=5,
            last_sent_at=now,
            created_at=now,
        )
    )
    db.commit()
    return code


def seed_phone_verification_code(
    client: TestClient,
    phone_number: str,
    purpose: str,
    code: str = "123456",
) -> str:
    override = app.dependency_overrides.get(get_db)
    if override is None:
        raise RuntimeError("get_db override is not configured for test client")

    db = next(override())
    settings = get_settings()
    normalized = normalize_phone_number(phone_number)
    now = utc_now()
    db.add(
        PhoneVerificationCode(
            id=str(uuid4()),
            phone_number=normalized,
            purpose=purpose,
            code_hash=hash_phone_code(
                normalized,
                purpose,
                code,
                settings.auth_phone_code_secret or settings.jwt_secret_key,
            ),
            expires_at=now + timedelta(minutes=10),
            attempt_count=0,
            max_attempts=5,
            last_sent_at=now,
            created_at=now,
        )
    )
    db.commit()
    return code


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}
