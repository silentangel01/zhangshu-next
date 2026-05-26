"""Tests for security properties."""

from __future__ import annotations

from tests.conftest import auth_headers, register_user


class TestPasswordSecurity:
    def test_password_hash_not_plaintext(self, client, db_session):
        register_user(client, email="sec@example.com", password="mysecretpass1")

        from app.repositories.user_repo import UserRepository

        repo = UserRepository(db_session)
        user = repo.get_by_email("sec@example.com")
        assert user is not None
        assert user.password_hash != "mysecretpass1"
        assert user.password_hash.startswith("$2b$")


class TestTokenSecurity:
    def test_refresh_token_not_stored_in_plaintext(self, client, db_session):
        result = register_user(client)
        refresh_token = result["refresh_token"]

        from app.models.refresh_token import RefreshToken

        tokens = list(db_session.query(RefreshToken).all())
        assert len(tokens) > 0
        for token in tokens:
            # jti_hash should not be the raw token
            assert token.jti_hash != refresh_token


class TestAuthProtection:
    def test_protected_endpoint_no_token(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code in (401, 403)

    def test_protected_endpoint_invalid_token(self, client):
        response = client.get(
            "/api/auth/me", headers=auth_headers("totally-fake-token")
        )
        assert response.status_code == 401


class TestCORS:
    def test_cors_not_wildcard(self, client):
        """Verify CORS middleware does not use '*' for origins."""
        from app.core.config import get_settings

        settings = get_settings()
        assert "*" not in settings.cors_origin_list
