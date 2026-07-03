"""Tests for email verification registration and login."""

from __future__ import annotations

from datetime import timedelta

from app.core.security import normalize_email
from app.models.email_verification_code import EmailVerificationCode
from app.models.user import User, utc_now
from tests.conftest import register_user, seed_email_verification_code


class TestEmailCheck:
    def test_email_check_available(self, client):
        response = client.post(
            "/api/auth/email/check",
            json={"email": "new@example.com"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "email": "new@example.com",
            "available": True,
        }

    def test_email_check_unavailable(self, client):
        register_user(client, email="taken@example.com")

        response = client.post(
            "/api/auth/email/check",
            json={"email": "taken@example.com"},
        )

        assert response.status_code == 200
        assert response.json()["available"] is False


class TestEmailCodeSend:
    def test_send_register_code_creates_active_code(self, client, db_session):
        response = client.post(
            "/api/auth/email-code/send",
            json={"email": "send-reg@example.com", "purpose": "register"},
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True

        rows = db_session.query(EmailVerificationCode).all()
        assert len(rows) == 1
        assert rows[0].email == "send-reg@example.com"
        assert rows[0].purpose == "register"
        assert rows[0].code_hash
        assert rows[0].code_hash != "123456"

    def test_send_register_code_rejects_registered_email(self, client):
        register_user(client, email="registered@example.com")

        response = client.post(
            "/api/auth/email-code/send",
            json={"email": "registered@example.com", "purpose": "register"},
        )

        assert response.status_code == 400
        assert "已注册" in response.json()["detail"]

    def test_send_login_code_unknown_email_is_generic(self, client, db_session):
        response = client.post(
            "/api/auth/email-code/send",
            json={"email": "missing@example.com", "purpose": "login"},
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert db_session.query(EmailVerificationCode).count() == 0


class TestRegisterWithEmailCode:
    def test_register_requires_code(self, client):
        response = client.post(
            "/api/auth/register",
            json={
                "email": "need-code@example.com",
                "password": "securepassword123",
                "display_name": "Need Code",
            },
        )

        assert response.status_code == 400
        assert "验证码" in response.json()["detail"]

    def test_register_with_valid_code_succeeds_and_consumes_code(
        self, client, db_session
    ):
        code = seed_email_verification_code(
            client, "valid-reg@example.com", "register"
        )

        response = client.post(
            "/api/auth/register",
            json={
                "email": "valid-reg@example.com",
                "password": "securepassword123",
                "display_name": "Valid",
                "verification_code": code,
            },
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

        row = db_session.query(EmailVerificationCode).one()
        assert row.consumed_at is not None

    def test_register_code_cannot_be_reused(self, client):
        code = seed_email_verification_code(
            client, "reuse-reg@example.com", "register"
        )
        first = client.post(
            "/api/auth/register",
            json={
                "email": "reuse-reg@example.com",
                "password": "securepassword123",
                "verification_code": code,
            },
        )
        assert first.status_code == 200

        second = client.post(
            "/api/auth/register",
            json={
                "email": "another-reuse@example.com",
                "password": "securepassword123",
                "verification_code": code,
            },
        )
        assert second.status_code == 401

    def test_register_expired_code_fails(self, client, db_session):
        code = seed_email_verification_code(
            client, "expired-reg@example.com", "register"
        )
        row = db_session.query(EmailVerificationCode).one()
        row.expires_at = utc_now() - timedelta(seconds=1)
        db_session.commit()

        response = client.post(
            "/api/auth/register",
            json={
                "email": "expired-reg@example.com",
                "password": "securepassword123",
                "verification_code": code,
            },
        )

        assert response.status_code == 401
        assert "验证码错误或已过期" in response.json()["detail"]

    def test_wrong_code_increments_attempts(self, client, db_session):
        seed_email_verification_code(client, "wrong-reg@example.com", "register")

        response = client.post(
            "/api/auth/register",
            json={
                "email": "wrong-reg@example.com",
                "password": "securepassword123",
                "verification_code": "000000",
            },
        )

        assert response.status_code == 401
        row = db_session.query(EmailVerificationCode).one()
        assert row.attempt_count == 1


class TestLoginWithEmailCode:
    def test_send_login_code_for_existing_user_creates_code(self, client, db_session):
        register_user(client, email="login-code-send@example.com")

        response = client.post(
            "/api/auth/email-code/send",
            json={"email": "login-code-send@example.com", "purpose": "login"},
        )

        assert response.status_code == 200
        row = (
            db_session.query(EmailVerificationCode)
            .filter_by(email="login-code-send@example.com", purpose="login")
            .one()
        )
        assert row.consumed_at is None

    def test_login_with_valid_email_code(self, client, db_session):
        register_user(client, email="code-login@example.com")
        code = seed_email_verification_code(client, "code-login@example.com", "login")

        response = client.post(
            "/api/auth/login/email-code",
            json={
                "email": "code-login@example.com",
                "verification_code": code,
            },
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

        user = db_session.query(User).filter_by(email="code-login@example.com").one()
        assert user.login_count >= 1

    def test_login_code_cannot_be_reused(self, client):
        register_user(client, email="reuse-login@example.com")
        code = seed_email_verification_code(client, "reuse-login@example.com", "login")

        first = client.post(
            "/api/auth/login/email-code",
            json={"email": "reuse-login@example.com", "verification_code": code},
        )
        assert first.status_code == 200

        second = client.post(
            "/api/auth/login/email-code",
            json={"email": "reuse-login@example.com", "verification_code": code},
        )
        assert second.status_code == 401

    def test_login_with_unknown_email_is_generic(self, client):
        response = client.post(
            "/api/auth/login/email-code",
            json={"email": "missing-login@example.com", "verification_code": "123456"},
        )

        assert response.status_code == 401
        assert "验证码错误或已过期" in response.json()["detail"]

    def test_rate_limit_keys_do_not_contain_raw_email(self, client, db_session):
        register_user(client, email="hash-code@example.com")
        seed_email_verification_code(client, "hash-code@example.com", "login")

        client.post(
            "/api/auth/login/email-code",
            json={"email": "hash-code@example.com", "verification_code": "000000"},
        )

        from app.models.rate_limit_event import RateLimitEvent

        events = db_session.query(RateLimitEvent).all()
        for event in events:
            assert "hash-code@example.com" not in event.key
            assert normalize_email("hash-code@example.com") not in event.key
