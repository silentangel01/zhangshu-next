"""Tests for authentication API endpoints."""

from __future__ import annotations

from tests.conftest import auth_headers, register_user


class TestRegister:
    def test_register_success(self, client):
        result = register_user(client)
        assert "access_token" in result
        assert "refresh_token" in result
        assert "user_id" in result

    def test_register_duplicate_email(self, client):
        register_user(client, email="dup@example.com")
        response = client.post(
            "/api/auth/register",
            json={
                "email": "dup@example.com",
                "password": "securepassword123",
                "display_name": "Another",
            },
        )
        assert response.status_code == 400
        assert "已注册" in response.json()["detail"]

    def test_register_short_password(self, client):
        response = client.post(
            "/api/auth/register",
            json={"email": "short@example.com", "password": "abc"},
        )
        assert response.status_code == 400
        assert "10" in response.json()["detail"]

    def test_register_empty_password(self, client):
        response = client.post(
            "/api/auth/register",
            json={"email": "empty@example.com", "password": "   "},
        )
        assert response.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        register_user(client, email="login@example.com", password="mypassword12")
        response = client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "mypassword12"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client):
        register_user(client, email="wrong@example.com", password="correctpass1")
        response = client.post(
            "/api/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        # Must not reveal whether user exists
        assert "邮箱或密码错误" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        response = client.post(
            "/api/auth/login",
            json={"email": "noone@example.com", "password": "whatever1234"},
        )
        assert response.status_code == 401
        assert "邮箱或密码错误" in response.json()["detail"]


class TestRefresh:
    def test_refresh_success(self, client):
        result = register_user(client)
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": result["refresh_token"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should be different (rotation)
        assert data["refresh_token"] != result["refresh_token"]

    def test_refresh_old_token_revoked(self, client):
        result = register_user(client)
        old_refresh = result["refresh_token"]

        # First refresh succeeds
        client.post("/api/auth/refresh", json={"refresh_token": old_refresh})

        # Second refresh with same token should fail
        response = client.post(
            "/api/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert response.status_code == 401

    def test_refresh_invalid_token(self, client):
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token-string"},
        )
        assert response.status_code == 401


class TestMe:
    def test_me_with_valid_token(self, client):
        result = register_user(
            client, email="me@example.com", display_name="Me User"
        )
        response = client.get(
            "/api/auth/me", headers=auth_headers(result["access_token"])
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@example.com"
        assert data["display_name"] == "Me User"

    def test_me_without_token(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code in (401, 403)

    def test_me_with_invalid_token(self, client):
        response = client.get(
            "/api/auth/me", headers=auth_headers("invalid-token")
        )
        assert response.status_code == 401
