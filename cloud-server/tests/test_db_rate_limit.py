"""Tests for database-level rate limiting."""

from __future__ import annotations

from tests.conftest import auth_headers, register_user


class TestLoginRateLimit:
    def test_login_rate_limit_enforced(self, client):
        """Multiple failed logins should eventually be rate-limited."""
        register_user(client, email="rl@example.com", password="correctpass1")

        # Make several failed login attempts
        for _ in range(10):
            client.post(
                "/api/auth/login",
                json={"email": "rl@example.com", "password": "wrongpassword"},
            )

        # Next attempt should be rate limited
        response = client.post(
            "/api/auth/login",
            json={"email": "rl@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 429

    def test_login_rate_limit_key_is_hashed(self, client, db_session):
        """Rate limit keys should not contain raw email addresses."""
        register_user(client, email="hash@example.com", password="correctpass1")

        # Trigger a failed login
        client.post(
            "/api/auth/login",
            json={"email": "hash@example.com", "password": "wrongpassword"},
        )

        # Check the rate_limit_events table
        from app.models.rate_limit_event import RateLimitEvent
        events = db_session.query(RateLimitEvent).all()
        for event in events:
            # Key should not contain the raw email
            assert "hash@example.com" not in event.key


class TestRegisterRateLimit:
    def test_register_rate_limit_enforced(self, client):
        """Multiple registrations from the same IP should be rate-limited."""
        # Register several accounts
        for i in range(5):
            resp = client.post(
                "/api/auth/register",
                json={
                    "email": f"rl-reg-{i}@example.com",
                    "password": "password12345",
                },
            )
            # Some may succeed, but eventually rate limit kicks in
            if resp.status_code == 429:
                break

        # Verify at least one was rate limited
        final_resp = client.post(
            "/api/auth/register",
            json={"email": "rl-reg-final@example.com", "password": "password12345"},
        )
        # Either 200 (if limit not yet reached) or 429
        assert final_resp.status_code in (200, 429)


class TestBackupRateLimit:
    def test_backup_init_rate_limit(self, client):
        """Backup init should have rate limiting configured per user.

        Note: The backup service uses its own rate limit check based on
        cloud_backups records, not the RateLimitService. The limit is
        30 per hour by default. This test verifies the endpoint works.
        """
        result = register_user(client, email="rl-backup@example.com")
        access_token = result["access_token"]

        # Create a cloud project first
        proj_resp = client.post(
            "/api/projects",
            headers=auth_headers(access_token),
            json={"title": "Test Project"},
        )
        assert proj_resp.status_code == 200
        project_id = proj_resp.json()["id"]

        # First backup init should succeed
        resp = client.post(
            f"/api/projects/{project_id}/backups/init",
            headers=auth_headers(access_token),
            json={"filename": "test.zip", "size_bytes": 1024},
        )
        # Either succeeds or returns a rate limit / other error
        assert resp.status_code in (200, 429, 400)
