"""Tests for cloud announcement proxy API in the backend sidecar."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.cloud import (  # noqa: E402
    get_announcement_service,
    get_auth_service,
    get_cloud_backup_service,
    get_feedback_service,
    get_network_service,
)
from app.main import app  # noqa: E402


@pytest.fixture
def mock_announcement_service():
    return MagicMock()


@pytest.fixture
def client(mock_announcement_service):
    app.dependency_overrides[get_announcement_service] = lambda: mock_announcement_service

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


class TestCloudAnnouncements:
    def test_returns_announcements(self, client, mock_announcement_service):
        mock_announcement_service.list_announcements.return_value = {
            "items": [
                {
                    "id": "ann-1",
                    "title": "测试公告",
                    "body": "正文",
                    "severity": "info",
                    "published_at": "2026-05-27T00:00:00Z",
                    "starts_at": None,
                    "ends_at": None,
                }
            ],
            "total": 1,
            "cloud_available": True,
        }

        response = client.get("/api/cloud/announcements")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["cloud_available"] is True
        mock_announcement_service.list_announcements.assert_called_once()

    def test_returns_empty_when_cloud_unavailable(
        self, client, mock_announcement_service
    ):
        mock_announcement_service.list_announcements.return_value = {
            "items": [],
            "total": 0,
            "cloud_available": False,
        }

        response = client.get("/api/cloud/announcements")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["cloud_available"] is False

    def test_passes_platform_param(self, client, mock_announcement_service):
        mock_announcement_service.list_announcements.return_value = {
            "items": [],
            "total": 0,
            "cloud_available": True,
        }

        client.get("/api/cloud/announcements?platform=windows")
        mock_announcement_service.list_announcements.assert_called_once_with(
            platform="windows", app_version=None
        )
