"""Tests for cloud API endpoints — dependency override approach."""

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


# ── Account Status ────────────────────────────────────────────────


def test_account_status_not_logged_in(client, mock_auth_service):
    mock_auth_service.get_account_status.return_value = {
        "logged_in": False,
        "cloud_available": False,
        "email": None,
        "display_name": None,
    }

    response = client.get("/api/cloud/account/status")
    assert response.status_code == 200
    data = response.json()
    assert data["logged_in"] is False
    assert data["cloud_available"] is False


def test_account_status_logged_in(client, mock_auth_service):
    mock_auth_service.get_account_status.return_value = {
        "logged_in": True,
        "cloud_available": True,
        "email": "test@example.com",
        "display_name": "test@example.com",
    }

    response = client.get("/api/cloud/account/status")
    assert response.status_code == 200
    data = response.json()
    assert data["logged_in"] is True
    assert data["email"] == "test@example.com"


# ── Login ─────────────────────────────────────────────────────────


def test_login_success(client, mock_auth_service):
    mock_auth_service.login.return_value = {
        "logged_in": True,
        "cloud_available": True,
        "email": "test@example.com",
        "display_name": "test@example.com",
    }

    response = client.post(
        "/api/cloud/auth/login",
        json={"email": "test@example.com", "password": "secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["logged_in"] is True
    mock_auth_service.login.assert_called_once_with("test@example.com", "secret")


def test_login_failure(client, mock_auth_service):
    from app.services.cloud_auth_service import CloudAuthError

    mock_auth_service.login.side_effect = CloudAuthError("密码错误")

    response = client.post(
        "/api/cloud/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_not_configured(client, mock_auth_service):
    from app.infrastructure.cloud_api_client import CloudApiNotConfiguredError

    mock_auth_service.login.side_effect = CloudApiNotConfiguredError("未配置")

    response = client.post(
        "/api/cloud/auth/login",
        json={"email": "test@example.com", "password": "secret"},
    )
    assert response.status_code == 503


# ── Logout ────────────────────────────────────────────────────────


def test_logout(client, mock_auth_service):
    response = client.post("/api/cloud/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_auth_service.logout.assert_called_once()


# ── Cloud Status ──────────────────────────────────────────────────


def test_cloud_status_not_enabled(client, mock_backup_service):
    mock_backup_service.get_status.return_value = {
        "cloud_enabled": False,
        "cloud_project_id": None,
        "provider": "zhangshu",
        "last_backup_at": None,
        "last_restore_at": None,
        "status": "inactive",
        "last_error": None,
    }

    response = client.get("/api/projects/some-proj/cloud/status")
    assert response.status_code == 200
    data = response.json()
    assert data["cloud_enabled"] is False


# ── Cloud Backups ─────────────────────────────────────────────────


def test_list_cloud_backups_empty(client, mock_backup_service):
    mock_backup_service.list_backups.return_value = []

    response = client.get("/api/projects/some-proj/cloud/backups")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_trigger_backup_success(client, mock_backup_service):
    from datetime import datetime, timezone
    from types import SimpleNamespace

    now = datetime.now(timezone.utc)
    record = SimpleNamespace(
        id="rec-1",
        project_id="some-proj",
        cloud_backup_id="backup-xyz",
        filename="test_backup.zip",
        size_bytes=1234,
        checksum_sha256="abc123",
        encryption_mode="none",
        status="success",
        error_message=None,
        created_at=now,
        uploaded_at=now,
    )
    mock_backup_service.trigger_backup.return_value = record

    response = client.post("/api/projects/some-proj/cloud/backups")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cloud_backup_id"] == "backup-xyz"


# ── Network Settings ────────────────────────────────────────────────


def test_get_network_settings(client, mock_network_service):
    mock_network_service.get_settings.return_value = {
        "mode": "auto",
        "last_working_mode": "secure_direct",
        "base_url_configured": True,
    }

    response = client.get("/api/cloud/network/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "auto"
    assert data["base_url_configured"] is True


def test_set_network_settings(client, mock_network_service):
    mock_network_service.set_mode.return_value = {
        "mode": "compat_no_sni",
        "last_working_mode": None,
        "base_url_configured": True,
    }

    response = client.put(
        "/api/cloud/network/settings",
        json={"mode": "compat_no_sni"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "compat_no_sni"


def test_set_network_settings_invalid_mode(client, mock_network_service):
    mock_network_service.set_mode.side_effect = ValueError("无效的连接模式")

    response = client.put(
        "/api/cloud/network/settings",
        json={"mode": "invalid"},
    )
    assert response.status_code == 400


# ── Network Diagnostics ─────────────────────────────────────────────


def test_run_diagnostics(client, mock_network_service):
    mock_network_service.run_diagnostics.return_value = {
        "ok": True,
        "recommended_mode": "secure_direct",
        "summary": "所有连接检测通过。",
        "steps": [
            {
                "name": "config_check",
                "ok": True,
                "latency_ms": None,
                "error_kind": "",
                "message": "已配置",
                "suggestion": "",
            }
        ],
    }

    response = client.post("/api/cloud/network/diagnose")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["steps"]) >= 1


# ── Error detail propagation ────────────────────────────────────────


def test_login_error_with_kind_and_suggestion(client, mock_auth_service):
    from app.services.cloud_auth_service import CloudAuthError

    mock_auth_service.login.side_effect = CloudAuthError(
        "连接超时",
        error_kind="timeout",
        suggestion="请检查网络连接",
    )

    response = client.post(
        "/api/cloud/auth/login",
        json={"email": "test@example.com", "password": "secret"},
    )
    assert response.status_code == 401
    data = response.json()
    # When error_kind is present, detail becomes a dict
    assert data["detail"]["error_kind"] == "timeout"
    assert data["detail"]["suggestion"] == "请检查网络连接"
