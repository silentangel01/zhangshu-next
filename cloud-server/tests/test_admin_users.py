"""Tests for admin user management API — list and detail."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, utc_now
from app.services.token_service import create_admin_access_token
from tests.conftest import auth_headers, register_user


def _make_admin(db_session: Session, email: str = "users-admin@example.com") -> str:
    user = User(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password("securepassword123"),
        display_name="Users Admin",
        is_active=True,
        is_admin=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(user)
    db_session.commit()
    return create_admin_access_token(user.id)


class TestAdminUsers:
    def test_no_auth_rejected(self, client: TestClient):
        response = client.get("/api/admin/users")
        assert response.status_code == 401

    def test_non_admin_rejected(self, client: TestClient, db_session: Session):
        data = register_user(client, email="user@example.com")
        headers = auth_headers(data["access_token"])
        response = client.get("/api/admin/users", headers=headers)
        assert response.status_code == 401

    def test_list_users(self, client: TestClient, db_session: Session):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        response = client.get("/api/admin/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        # At least the admin user itself
        assert data["total"] >= 1

    def test_list_with_keyword(self, client: TestClient, db_session: Session):
        token = _make_admin(db_session)
        headers = auth_headers(token)

        # Create an additional user with a distinctive email
        other = User(
            id=str(uuid4()),
            email="searchable-user@example.com",
            password_hash=hash_password("securepassword123"),
            display_name="Searchable",
            is_active=True,
            is_admin=False,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db_session.add(other)
        db_session.commit()

        response = client.get(
            "/api/admin/users?keyword=searchable", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "searchable" in data["items"][0]["email"].lower()

    def test_get_user_detail(self, client: TestClient, db_session: Session):
        token = _make_admin(db_session)
        headers = auth_headers(token)

        # Get the admin's own user ID from the list
        list_resp = client.get("/api/admin/users", headers=headers)
        admin_id = list_resp.json()["items"][0]["id"]

        response = client.get(f"/api/admin/users/{admin_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == admin_id
        assert "email" in data
        assert "cloud_project_count" in data

    def test_get_nonexistent_user(self, client: TestClient, db_session: Session):
        token = _make_admin(db_session)
        headers = auth_headers(token)
        response = client.get(
            "/api/admin/users/00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
        assert response.status_code == 404
