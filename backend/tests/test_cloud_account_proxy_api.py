"""Tests for cloud account proxy API endpoints (desktop backend forwarding)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.cloud import (  # noqa: E402
    get_auth_service,
    get_cloud_backup_service,
    get_network_service,
)
from app.main import app  # noqa: E402
from app.services.cloud_auth_service import CloudAuthError  # noqa: E402


@pytest.fixture
def mock_auth_service():
    return MagicMock()


@pytest.fixture
def mock_backup_service():
    return MagicMock()


@pytest.fixture
def mock_network_service():
    return MagicMock()


@pytest.fixture
def client(mock_auth_service, mock_backup_service, mock_network_service):
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[get_cloud_backup_service] = lambda: mock_backup_service
    app.dependency_overrides[get_network_service] = lambda: mock_network_service

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


# ── Profile ──────────────────────────────────────────────────────────


def test_get_profile(client, mock_auth_service):
    mock_auth_service.get_account_profile.return_value = {
        "id": "user-123",
        "email": "user@example.com",
        "display_name": "Test User",
        "created_at": "2025-01-01T00:00:00",
    }

    response = client.get("/api/cloud/account/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["display_name"] == "Test User"


def test_get_profile_unauthorized(client, mock_auth_service):
    mock_auth_service.get_account_profile.side_effect = CloudAuthError("Not logged in")

    response = client.get("/api/cloud/account/profile")
    assert response.status_code == 401


def test_update_profile(client, mock_auth_service):
    mock_auth_service.update_account_profile.return_value = {
        "id": "user-123",
        "email": "user@example.com",
        "display_name": "New Name",
        "created_at": "2025-01-01T00:00:00",
    }

    response = client.patch(
        "/api/cloud/account/profile",
        json={"display_name": "New Name"},
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "New Name"
    mock_auth_service.update_account_profile.assert_called_once_with("New Name")


# ── Password ─────────────────────────────────────────────────────────


def test_change_password(client, mock_auth_service):
    mock_auth_service.change_password.return_value = {"ok": True}

    response = client.post(
        "/api/cloud/account/password/change",
        json={"old_password": "old123", "new_password": "new12345"},
    )
    assert response.status_code == 200
    mock_auth_service.change_password.assert_called_once_with("old123", "new12345")
    # After password change, logout should be called
    mock_auth_service.logout.assert_called_once()


def test_change_password_error(client, mock_auth_service):
    mock_auth_service.change_password.side_effect = CloudAuthError("Wrong password")

    response = client.post(
        "/api/cloud/account/password/change",
        json={"old_password": "wrong", "new_password": "new12345"},
    )
    assert response.status_code == 400
    mock_auth_service.logout.assert_not_called()


# ── Sessions ─────────────────────────────────────────────────────────


def test_revoke_all_sessions(client, mock_auth_service):
    mock_auth_service.revoke_all_sessions.return_value = {"revoked_count": 3}

    response = client.post("/api/cloud/account/sessions/revoke-all")
    assert response.status_code == 200
    assert response.json()["revoked_count"] == 3
    # After revoking all sessions, logout should be called
    mock_auth_service.logout.assert_called_once()


# ── Usage ────────────────────────────────────────────────────────────


def test_get_usage(client, mock_auth_service):
    mock_auth_service.get_usage.return_value = {
        "storage_used_bytes": 1024,
        "storage_quota_bytes": 1073741824,
        "backup_count": 5,
        "backup_count_quota": 100,
        "backup_init_used_last_hour": 2,
        "backup_init_limit_per_hour": 30,
        "max_backup_size_bytes": 524288000,
    }

    response = client.get("/api/cloud/account/usage")
    assert response.status_code == 200
    data = response.json()
    assert data["storage_used_bytes"] == 1024
    assert data["backup_count"] == 5


# ── Export ───────────────────────────────────────────────────────────


def test_export_data(client, mock_auth_service):
    mock_auth_service.export_account_data.return_value = {
        "account": {"id": "user-123", "email": "user@example.com"},
        "projects": [],
        "backups": [],
        "exported_at": "2025-01-01T00:00:00",
    }

    response = client.get("/api/cloud/account/export")
    assert response.status_code == 200
    assert "account" in response.json()


# ── Deletion ─────────────────────────────────────────────────────────


def test_request_deletion(client, mock_auth_service):
    mock_auth_service.request_account_deletion.return_value = {
        "request_id": "req-123",
        "expires_at": "2025-01-01T01:00:00",
        "project_count": 2,
        "backup_count": 10,
        "total_size_bytes": 12345,
        "confirmation_text": "DELETE MY CLOUD DATA",
    }

    response = client.post(
        "/api/cloud/account/delete-request",
        json={"password": "mypassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "req-123"
    assert data["confirmation_text"] == "DELETE MY CLOUD DATA"


def test_confirm_deletion(client, mock_auth_service):
    mock_auth_service.confirm_account_deletion.return_value = {"deleted": True}

    response = client.request(
        "DELETE",
        "/api/cloud/account",
        json={
            "request_id": "req-123",
            "confirmation_text": "DELETE MY CLOUD DATA",
        },
    )
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    # After account deletion, logout should be called
    mock_auth_service.logout.assert_called_once()


def test_confirm_deletion_error(client, mock_auth_service):
    mock_auth_service.confirm_account_deletion.side_effect = CloudAuthError(
        "Invalid confirmation"
    )

    response = client.request(
        "DELETE",
        "/api/cloud/account",
        json={
            "request_id": "req-123",
            "confirmation_text": "WRONG",
        },
    )
    assert response.status_code == 400
    mock_auth_service.logout.assert_not_called()
