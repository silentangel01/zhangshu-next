"""Tests for admin authentication API — login, refresh, logout, me."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, utc_now


def _make_admin(
    db_session: Session,
    email: str = "auth-admin@example.com",
    password: str = "securepassword123",
) -> str:
    """Create admin user directly in DB. Returns the email."""
    user = User(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password(password),
        display_name="Auth Admin",
        is_active=True,
        is_admin=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return email


def _make_non_admin(
    db_session: Session,
    email: str = "normal@example.com",
    password: str = "securepassword123",
) -> str:
    """Create a non-admin user directly in DB. Returns the email."""
    user = User(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password(password),
        display_name="Normal User",
        is_active=True,
        is_admin=False,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return email


class TestAdminAuth:
    def test_login_success(self, client: TestClient, db_session: Session):
        email = _make_admin(db_session)
        response = client.post(
            "/api/admin/auth/login",
            json={"email": email, "password": "securepassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        # Cookies should be set
        assert "zs_admin_token" in response.cookies
        assert "zs_admin_refresh" in response.cookies

    def test_login_wrong_password(self, client: TestClient, db_session: Session):
        _make_admin(db_session)
        response = client.post(
            "/api/admin/auth/login",
            json={"email": "auth-admin@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_non_admin(self, client: TestClient, db_session: Session):
        email = _make_non_admin(db_session)
        response = client.post(
            "/api/admin/auth/login",
            json={"email": email, "password": "securepassword123"},
        )
        assert response.status_code == 403

    def test_login_nonexistent_user(self, client: TestClient):
        response = client.post(
            "/api/admin/auth/login",
            json={"email": "nobody@example.com", "password": "whatever"},
        )
        assert response.status_code == 401

    def test_refresh_success(self, client: TestClient, db_session: Session):
        email = _make_admin(db_session)
        # Login to get cookies
        login_resp = client.post(
            "/api/admin/auth/login",
            json={"email": email, "password": "securepassword123"},
        )
        assert login_resp.status_code == 200

        # Extract cookies manually (secure cookies not auto-sent by TestClient)
        cookies = {
            name: value for name, value in login_resp.cookies.items()
        }

        # Refresh using the extracted cookies
        refresh_resp = client.post("/api/admin/auth/refresh", cookies=cookies)
        assert refresh_resp.status_code == 200
        assert refresh_resp.json()["ok"] is True
        # New cookies should be set
        assert "zs_admin_token" in refresh_resp.cookies

    def test_logout_success(self, client: TestClient, db_session: Session):
        email = _make_admin(db_session)
        client.post(
            "/api/admin/auth/login",
            json={"email": email, "password": "securepassword123"},
        )
        logout_resp = client.post("/api/admin/auth/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["ok"] is True

    def test_me_success(self, client: TestClient, db_session: Session):
        email = _make_admin(db_session)
        login_resp = client.post(
            "/api/admin/auth/login",
            json={"email": email, "password": "securepassword123"},
        )
        assert login_resp.status_code == 200

        # Extract cookies manually (secure cookies not auto-sent by TestClient)
        cookies = {
            name: value for name, value in login_resp.cookies.items()
        }

        me_resp = client.get("/api/admin/auth/me", cookies=cookies)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == email

    def test_me_no_auth(self, client: TestClient):
        response = client.get("/api/admin/auth/me")
        assert response.status_code == 401
