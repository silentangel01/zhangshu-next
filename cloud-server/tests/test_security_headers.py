"""Tests for security response headers middleware."""

from __future__ import annotations

from tests.conftest import register_user


class TestSecurityHeaders:
    def test_nosniff_header(self, client):
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_frame_options_header(self, client):
        response = client.get("/health")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy_header(self, client):
        response = client.get("/health")
        assert response.headers.get("Referrer-Policy") == "no-referrer"

    def test_permissions_policy_header(self, client):
        response = client.get("/health")
        assert "camera=()" in response.headers.get("Permissions-Policy", "")

    def test_auth_response_no_cache(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "email": "cache@example.com",
                "password": "securepassword123",
                "display_name": "Test",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("Cache-Control") == "no-store"
        assert response.headers.get("Pragma") == "no-cache"

    def test_login_no_cache(self, client):
        register_user(client)
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 200
        assert response.headers.get("Cache-Control") == "no-store"

    def test_non_auth_no_cache_control(self, client):
        response = client.get("/health")
        # /health should NOT have no-store
        assert response.headers.get("Cache-Control") != "no-store"


class TestRequestID:
    def test_request_id_in_response(self, client):
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_request_id_preserved(self, client):
        custom_id = "test-request-123"
        response = client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.headers["X-Request-ID"] == custom_id

    def test_different_requests_different_ids(self, client):
        r1 = client.get("/health")
        r2 = client.get("/health")
        # Auto-generated IDs should differ
        assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]
