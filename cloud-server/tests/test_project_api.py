"""Tests for project API endpoints."""

from __future__ import annotations

from tests.conftest import auth_headers, register_user


class TestCreateProject:
    def test_create_success(self, client):
        result = register_user(client)
        response = client.post(
            "/api/projects",
            json={"title": "测试作品"},
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "测试作品"
        assert data["owner_id"] == result["user_id"]
        assert "id" in data
        assert "created_at" in data

    def test_create_without_auth(self, client):
        response = client.post("/api/projects", json={"title": "No Auth"})
        assert response.status_code in (401, 403)

    def test_create_empty_title(self, client):
        result = register_user(client)
        response = client.post(
            "/api/projects",
            json={"title": "   "},
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 400


class TestListProjects:
    def test_list_own_projects(self, client):
        result = register_user(client, email="list@example.com")
        headers = auth_headers(result["access_token"])

        client.post("/api/projects", json={"title": "作品A"}, headers=headers)
        client.post("/api/projects", json={"title": "作品B"}, headers=headers)

        response = client.get("/api/projects", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        titles = {item["title"] for item in data["items"]}
        assert "作品A" in titles
        assert "作品B" in titles

    def test_list_isolation(self, client):
        # User A creates a project
        user_a = register_user(client, email="usera@example.com")
        client.post(
            "/api/projects",
            json={"title": "User A Project"},
            headers=auth_headers(user_a["access_token"]),
        )

        # User B should not see User A's project
        user_b = register_user(client, email="userb@example.com")
        response = client.get(
            "/api/projects", headers=auth_headers(user_b["access_token"])
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_list_without_auth(self, client):
        response = client.get("/api/projects")
        assert response.status_code in (401, 403)
