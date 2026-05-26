"""Tests for /health and /ready endpoints."""

from __future__ import annotations


class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestReady:
    def test_ready_returns_ok(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "degraded")
        assert "checks" in data

    def test_ready_database_check(self, client):
        response = client.get("/ready")
        data = response.json()
        # In test environment with SQLite in-memory, database should be ok
        assert data["checks"]["database"] == "ok"

    def test_ready_oss_config_check(self, client):
        response = client.get("/ready")
        data = response.json()
        # Test conftest sets OSS credentials
        assert data["checks"]["oss_config"] == "ok"

    def test_ready_has_alembic_field(self, client):
        response = client.get("/ready")
        data = response.json()
        assert "alembic_head" in data["checks"]
