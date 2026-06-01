"""Tests for account management API endpoints."""

from __future__ import annotations

from tests.conftest import auth_headers, register_user


class TestProfile:
    def test_get_profile(self, client):
        result = register_user(
            client, email="profile@example.com", display_name="Profile User"
        )
        response = client.get(
            "/api/account/profile",
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profile@example.com"
        assert data["display_name"] == "Profile User"
        assert "id" in data
        assert "created_at" in data

    def test_get_profile_no_auth(self, client):
        response = client.get("/api/account/profile")
        assert response.status_code in (401, 403)

    def test_update_profile(self, client):
        result = register_user(client, email="update@example.com")
        response = client.patch(
            "/api/account/profile",
            headers=auth_headers(result["access_token"]),
            json={"display_name": "New Display Name"},
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "New Display Name"

    def test_update_profile_empty_name(self, client):
        result = register_user(client, email="empty-name@example.com")
        response = client.patch(
            "/api/account/profile",
            headers=auth_headers(result["access_token"]),
            json={"display_name": ""},
        )
        # Empty display name is not allowed
        assert response.status_code == 400


class TestChangePassword:
    def test_change_password_success(self, client):
        result = register_user(
            client, email="chpw@example.com", password="oldpassword1"
        )
        old_refresh = result["refresh_token"]

        response = client.post(
            "/api/account/password/change",
            headers=auth_headers(result["access_token"]),
            json={"old_password": "oldpassword1", "new_password": "newpassword1"},
        )
        assert response.status_code == 200

        # Old refresh token should be revoked
        refresh_resp = client.post(
            "/api/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert refresh_resp.status_code == 401

        # Login with new password works
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "chpw@example.com", "password": "newpassword1"},
        )
        assert login_resp.status_code == 200

    def test_change_password_wrong_old(self, client):
        result = register_user(
            client, email="chpw-wrong@example.com", password="correctpass1"
        )
        response = client.post(
            "/api/account/password/change",
            headers=auth_headers(result["access_token"]),
            json={"old_password": "wrongoldpass", "new_password": "newpassword1"},
        )
        assert response.status_code == 400

    def test_change_password_short_new(self, client):
        result = register_user(
            client, email="chpw-short@example.com", password="correctpass1"
        )
        response = client.post(
            "/api/account/password/change",
            headers=auth_headers(result["access_token"]),
            json={"old_password": "correctpass1", "new_password": "short"},
        )
        assert response.status_code == 400


class TestSessions:
    def test_list_sessions(self, client):
        result = register_user(client, email="sessions@example.com")
        response = client.get(
            "/api/account/sessions",
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert data["total"] >= 1

    def test_revoke_all_sessions(self, client):
        result = register_user(client, email="revoke@example.com")
        old_refresh = result["refresh_token"]

        response = client.post(
            "/api/account/sessions/revoke-all",
            headers=auth_headers(result["access_token"]),
        )
        assert response.status_code == 200
        assert response.json()["revoked_count"] >= 1

        # Old refresh token should be revoked
        refresh_resp = client.post(
            "/api/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert refresh_resp.status_code == 401
