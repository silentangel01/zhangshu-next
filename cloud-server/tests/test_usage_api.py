"""Tests for usage API endpoint."""

from __future__ import annotations

from tests.conftest import auth_headers, register_user


class TestUsage:
    def test_get_usage(self, client):
        result = register_user(client, email="usage@example.com")
        response = client.get(
            "/api/account/usage",
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert "storage_used_bytes" in data
        assert "storage_quota_bytes" in data
        assert "backup_count" in data
        assert "backup_count_quota" in data
        assert "backup_init_used_last_hour" in data
        assert "backup_init_limit_per_hour" in data
        assert "max_backup_size_bytes" in data
        assert data["storage_quota_bytes"] > 0
        assert data["backup_count_quota"] > 0

    def test_get_usage_no_auth(self, client):
        response = client.get("/api/account/usage")
        assert response.status_code in (401, 403)

    def test_usage_initial_zeros(self, client):
        result = register_user(client, email="usage-zero@example.com")
        response = client.get(
            "/api/account/usage",
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["storage_used_bytes"] == 0
        assert data["backup_count"] == 0
