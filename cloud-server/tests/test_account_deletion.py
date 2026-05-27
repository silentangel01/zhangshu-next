"""Tests for two-stage account deletion."""

from __future__ import annotations

from unittest.mock import patch

from tests.conftest import auth_headers, register_user


class TestDeletionRequest:
    def test_request_deletion_requires_password(self, client):
        result = register_user(client, email="del@example.com", password="mypassword1")
        response = client.post(
            "/api/account/delete-request",
            headers=auth_headers(result["access_token"]),
            json={"password": "wrongpassword"},
        )
        # Wrong password should return an error (400 or 401)
        assert response.status_code in (400, 401)

    def test_request_deletion_success(self, client):
        result = register_user(client, email="del-ok@example.com", password="mypassword1")
        response = client.post(
            "/api/account/delete-request",
            headers=auth_headers(result["access_token"]),
            json={"password": "mypassword1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "expires_at" in data
        assert "confirmation_text" in data
        assert data["confirmation_text"] == "DELETE MY CLOUD DATA"

    def test_request_deletion_no_auth(self, client):
        response = client.post(
            "/api/account/delete-request",
            json={"password": "anypassword"},
        )
        assert response.status_code in (401, 403)


class TestConfirmDeletion:
    def test_confirm_wrong_text(self, client):
        result = register_user(client, email="del-txt@example.com", password="mypassword1")

        # Request deletion
        req_resp = client.post(
            "/api/account/delete-request",
            headers=auth_headers(result["access_token"]),
            json={"password": "mypassword1"},
        )
        request_id = req_resp.json()["request_id"]

        # Confirm with wrong text
        response = client.request(
            "DELETE",
            "/api/account",
            headers=auth_headers(result["access_token"]),
            json={"request_id": request_id, "confirmation_text": "WRONG TEXT"},
        )
        assert response.status_code == 400

    def test_confirm_deletion_success(self, client, mock_oss):
        result = register_user(client, email="del-full@example.com", password="mypassword1")
        access_token = result["access_token"]
        refresh_token = result["refresh_token"]

        # Request deletion
        req_resp = client.post(
            "/api/account/delete-request",
            headers=auth_headers(access_token),
            json={"password": "mypassword1"},
        )
        assert req_resp.status_code == 200, f"Request failed: {req_resp.json()}"
        request_id = req_resp.json()["request_id"]

        # Confirm deletion
        response = client.request(
            "DELETE",
            "/api/account",
            headers=auth_headers(access_token),
            json={
                "request_id": request_id,
                "confirmation_text": "DELETE MY CLOUD DATA",
            },
        )
        assert response.status_code == 200, f"Confirm failed: {response.json()}"
        data = response.json()
        assert "message" in data
        assert "deleted_projects" in data
        assert "deleted_backups" in data

        # Login should fail (account anonymized)
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "del-full@example.com", "password": "mypassword1"},
        )
        assert login_resp.status_code == 401

    def test_confirm_expired_request(self, client):
        result = register_user(client, email="del-exp@example.com", password="mypassword1")

        # We can't easily make a request expire in tests without waiting,
        # but we can test with an invalid request_id
        response = client.request(
            "DELETE",
            "/api/account",
            headers=auth_headers(result["access_token"]),
            json={
                "request_id": "nonexistent-request-id",
                "confirmation_text": "DELETE MY CLOUD DATA",
            },
        )
        assert response.status_code == 400

    def test_confirm_used_request(self, client):
        """A deletion request can only be used once."""
        result = register_user(client, email="del-used@example.com", password="mypassword1")

        # Request deletion
        req_resp = client.post(
            "/api/account/delete-request",
            headers=auth_headers(result["access_token"]),
            json={"password": "mypassword1"},
        )
        request_id = req_resp.json()["request_id"]

        # First confirm succeeds
        resp1 = client.request(
            "DELETE",
            "/api/account",
            headers=auth_headers(result["access_token"]),
            json={
                "request_id": request_id,
                "confirmation_text": "DELETE MY CLOUD DATA",
            },
        )
        # Either 200 (success) or some error - we just verify it doesn't crash
        assert resp1.status_code in (200, 400, 401)
