"""Tests for cloud feedback proxy API in the backend sidecar."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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
from app.services.cloud_feedback_service import CloudFeedbackError  # noqa: E402


@pytest.fixture
def mock_feedback_service():
    svc = MagicMock()
    svc.submit_feedback = AsyncMock()
    return svc


@pytest.fixture
def client(mock_feedback_service):
    app.dependency_overrides[get_feedback_service] = lambda: mock_feedback_service

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


class TestCloudFeedback:
    def test_successful_text_feedback(self, client, mock_feedback_service):
        mock_feedback_service.submit_feedback.return_value = {
            "id": "fb-001",
            "status": "open",
            "uploaded_attachments": 0,
            "failed_attachments": 0,
        }

        response = client.post(
            "/api/cloud/feedback",
            data={
                "category": "suggestion",
                "title": "建议",
                "description": "这是一条建议，至少十个字符。",
                "include_diagnostics": "true",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "fb-001"

    def test_feedback_with_attachment(self, client, mock_feedback_service):
        mock_feedback_service.submit_feedback.return_value = {
            "id": "fb-002",
            "status": "open",
            "uploaded_attachments": 1,
            "failed_attachments": 0,
        }

        response = client.post(
            "/api/cloud/feedback",
            data={
                "category": "bug",
                "title": "UI 异常",
                "description": "界面在特定分辨率下显示异常。",
                "include_diagnostics": "false",
            },
            files=[
                ("attachments", ("screenshot.png", b"\x89PNG" + b"\x00" * 100, "image/png"))
            ],
        )
        assert response.status_code == 200
        assert response.json()["uploaded_attachments"] == 1

    def test_cloud_not_configured(self, client, mock_feedback_service):
        from app.infrastructure.cloud_api_client import CloudApiNotConfiguredError

        mock_feedback_service.submit_feedback.side_effect = CloudApiNotConfiguredError(
            "云服务未配置"
        )

        response = client.post(
            "/api/cloud/feedback",
            data={
                "category": "bug",
                "title": "测试",
                "description": "测试描述至少十个字符。",
                "include_diagnostics": "false",
            },
        )
        assert response.status_code == 503

    def test_feedback_error(self, client, mock_feedback_service):
        mock_feedback_service.submit_feedback.side_effect = CloudFeedbackError(
            "附件数量不能超过 5 个。"
        )

        response = client.post(
            "/api/cloud/feedback",
            data={
                "category": "bug",
                "title": "测试",
                "description": "测试描述至少十个字符。",
                "include_diagnostics": "false",
            },
        )
        assert response.status_code == 400
        assert "附件数量" in response.json()["detail"]
