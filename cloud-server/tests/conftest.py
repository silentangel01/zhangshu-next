"""Shared test fixtures."""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

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

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402

# Import all models BEFORE importing app — `import app.models.X` rebinds
# the name `app` to the package module, shadowing the FastAPI instance.
import app.models.user  # noqa: E402, F401
import app.models.refresh_token  # noqa: E402, F401
import app.models.cloud_project  # noqa: E402, F401
import app.models.cloud_backup  # noqa: E402, F401
import app.models.rate_limit_event  # noqa: E402, F401
import app.models.account_deletion_request  # noqa: E402, F401
import app.models.announcement  # noqa: E402, F401
import app.models.feedback_ticket  # noqa: E402, F401
import app.models.feedback_attachment  # noqa: E402, F401

from app.main import app  # noqa: E402 — must come AFTER model imports


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
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    return response.json()


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}
