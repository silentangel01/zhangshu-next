"""Tests for public feedback API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import register_user, auth_headers


class TestCreateFeedback:
    def test_anonymous_text_feedback(self, client: TestClient, mock_oss):
        response = client.post(
            "/api/feedback",
            json={
                "category": "bug",
                "title": "按钮无响应",
                "description": "点击云备份按钮后没有任何反应，已经尝试多次。",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"]
        assert data["status"] == "open"
        assert data["upload_slots"] == []

    def test_authenticated_feedback(
        self, client: TestClient, db_session: Session, mock_oss
    ):
        reg = register_user(client, email="user@example.com")
        headers = auth_headers(reg["access_token"])

        response = client.post(
            "/api/feedback",
            headers=headers,
            json={
                "category": "suggestion",
                "title": "希望支持暗色主题",
                "description": "在夜间写作时希望有暗色主题保护眼睛。",
            },
        )
        assert response.status_code == 201

    def test_feedback_with_attachments(self, client: TestClient, mock_oss):
        mock_oss.generate_put_url.return_value = "https://oss.example.com/put"
        response = client.post(
            "/api/feedback",
            json={
                "category": "bug",
                "title": "UI 显示异常",
                "description": "章节编辑器在特定分辨率下显示异常，详见截图。",
                "attachments": [
                    {
                        "filename": "screenshot.png",
                        "content_type": "image/png",
                        "size_bytes": 1024,
                    }
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["upload_slots"]) == 1
        assert data["upload_slots"][0]["upload_url"]

    def test_reject_invalid_category(self, client: TestClient, mock_oss):
        response = client.post(
            "/api/feedback",
            json={
                "category": "invalid",
                "title": "测试",
                "description": "测试描述至少十个字符。",
            },
        )
        assert response.status_code == 422

    def test_reject_short_description(self, client: TestClient, mock_oss):
        response = client.post(
            "/api/feedback",
            json={
                "category": "bug",
                "title": "测试",
                "description": "太短",
            },
        )
        assert response.status_code == 422

    def test_reject_too_many_attachments(self, client: TestClient, mock_oss):
        attachments = [
            {"filename": f"file{i}.png", "content_type": "image/png", "size_bytes": 100}
            for i in range(6)
        ]
        response = client.post(
            "/api/feedback",
            json={
                "category": "bug",
                "title": "测试",
                "description": "测试描述至少十个字符。",
                "attachments": attachments,
            },
        )
        assert response.status_code == 400

    def test_reject_invalid_content_type(self, client: TestClient, mock_oss):
        response = client.post(
            "/api/feedback",
            json={
                "category": "bug",
                "title": "测试",
                "description": "测试描述至少十个字符。",
                "attachments": [
                    {
                        "filename": "virus.exe",
                        "content_type": "application/x-msdownload",
                        "size_bytes": 100,
                    }
                ],
            },
        )
        assert response.status_code == 400

    def test_reject_oversized_attachment(self, client: TestClient, mock_oss):
        response = client.post(
            "/api/feedback",
            json={
                "category": "bug",
                "title": "测试",
                "description": "测试描述至少十个字符。",
                "attachments": [
                    {
                        "filename": "huge.mp4",
                        "content_type": "video/mp4",
                        "size_bytes": 100_000_000,
                    }
                ],
            },
        )
        assert response.status_code == 400


class TestCompleteFeedback:
    def test_complete_with_no_uploads(self, client: TestClient, mock_oss):
        # Create feedback first
        create_resp = client.post(
            "/api/feedback",
            json={
                "category": "bug",
                "title": "测试",
                "description": "测试描述至少十个字符。",
            },
        )
        feedback_id = create_resp.json()["id"]

        # Complete
        response = client.post(
            f"/api/feedback/{feedback_id}/complete",
            json={"uploads": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["uploaded_attachments"] == 0
        assert data["failed_attachments"] == 0

    def test_complete_nonexistent(self, client: TestClient, mock_oss):
        response = client.post(
            "/api/feedback/nonexistent-id/complete",
            json={"uploads": []},
        )
        assert response.status_code == 404
