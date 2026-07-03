"""Email verification code service for auth flows."""

from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta
from typing import Callable, Literal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import normalize_email, sha256_text
from app.infrastructure.email_sender import EmailDeliveryError, EmailSender
from app.models.email_verification_code import EmailVerificationCode
from app.models.user import utc_now
from app.repositories.email_verification_repo import EmailVerificationCodeRepository
from app.repositories.auth_identity_repo import AuthIdentityRepository
from app.repositories.user_repo import UserRepository

EmailCodePurpose = Literal["register", "login", "bind"]

_INVALID_CODE_MESSAGE = "验证码错误或已过期。"


class EmailVerificationError(Exception):
    """Raised for verification-code failures safe to expose to callers."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        reason_code: str = "email_verification_failed",
    ):
        super().__init__(message)
        self.status_code = status_code
        self.reason_code = reason_code


def hash_email_code(
    email: str,
    purpose: str,
    code: str,
    secret: str,
) -> str:
    """Hash an email verification code with server-side secret material."""
    normalized = normalize_email(email)
    return sha256_text(f"{secret}:{purpose}:{normalized}:{code.strip()}")


class EmailVerificationService:
    def __init__(
        self,
        db: Session,
        *,
        sender: EmailSender | None = None,
        settings: Settings | None = None,
        now_fn: Callable[[], datetime] = utc_now,
    ):
        self._db = db
        self._settings = settings or get_settings()
        self._sender = sender or EmailSender(self._settings)
        self._repo = EmailVerificationCodeRepository(db)
        self._user_repo = UserRepository(db)
        self._identity_repo = AuthIdentityRepository(db)
        self._now_fn = now_fn

    def send_code(self, email: str, purpose: EmailCodePurpose) -> dict:
        normalized = normalize_email(email)
        now = self._now()
        existing_user = self._user_repo.get_by_email(normalized)
        existing_identity = self._identity_repo.get_by_provider_identifier(
            "email", normalized
        )

        if purpose in {"register", "bind"} and (
            existing_user is not None or existing_identity is not None
        ):
            raise EmailVerificationError(
                "该邮箱已注册，请直接登录。",
                status_code=400,
                reason_code="email_registered",
            )

        expires_in = self._settings.auth_email_code_ttl_seconds
        cooldown = self._settings.auth_email_code_resend_cooldown_seconds

        if purpose == "login" and existing_user is None:
            return {
                "ok": True,
                "expires_in_seconds": expires_in,
                "cooldown_seconds": cooldown,
            }

        latest = self._repo.get_latest_active(normalized, purpose, now)
        if latest is not None:
            next_allowed_at = latest.last_sent_at + timedelta(seconds=cooldown)
            if next_allowed_at > now:
                raise EmailVerificationError(
                    "验证码发送过于频繁，请稍后再试。",
                    status_code=429,
                    reason_code="cooldown",
                )

        code = self._generate_code()
        expires_at = now + timedelta(seconds=expires_in)
        code_hash = hash_email_code(
            normalized,
            purpose,
            code,
            self._settings.auth_email_code_secret or self._settings.jwt_secret_key,
        )

        self._repo.consume_active_for_email(
            normalized, purpose, now, commit=False
        )
        row = EmailVerificationCode(
            id=str(uuid4()),
            email=normalized,
            purpose=purpose,
            code_hash=code_hash,
            expires_at=expires_at,
            attempt_count=0,
            max_attempts=self._settings.auth_email_code_max_attempts,
            last_sent_at=now,
            created_at=now,
        )
        self._repo.create(row)

        try:
            self._sender.send_verification_code(
                normalized,
                code,
                purpose,
                max(1, expires_in // 60),
            )
        except EmailDeliveryError as exc:
            self._repo.mark_consumed(row, self._now())
            raise EmailVerificationError(
                str(exc),
                status_code=503,
                reason_code="email_delivery_failed",
            ) from exc

        return {
            "ok": True,
            "expires_in_seconds": expires_in,
            "cooldown_seconds": cooldown,
        }

    def verify_code(
        self,
        email: str,
        purpose: EmailCodePurpose,
        code: str,
    ) -> None:
        normalized = normalize_email(email)
        candidate = code.strip()
        if not candidate.isdigit():
            raise EmailVerificationError(
                _INVALID_CODE_MESSAGE,
                status_code=401,
                reason_code="invalid_code",
            )

        now = self._now()
        row = self._repo.get_latest_active(normalized, purpose, now)
        if row is None:
            raise EmailVerificationError(
                _INVALID_CODE_MESSAGE,
                status_code=401,
                reason_code="missing_or_expired",
            )

        if row.attempt_count >= row.max_attempts:
            self._repo.mark_consumed(row, now)
            raise EmailVerificationError(
                _INVALID_CODE_MESSAGE,
                status_code=401,
                reason_code="max_attempts",
            )

        expected = hash_email_code(
            normalized,
            purpose,
            candidate,
            self._settings.auth_email_code_secret or self._settings.jwt_secret_key,
        )
        if not hmac.compare_digest(expected, row.code_hash):
            self._repo.increment_attempts(row, commit=False)
            if row.attempt_count >= row.max_attempts:
                row.consumed_at = now
            self._db.commit()
            raise EmailVerificationError(
                _INVALID_CODE_MESSAGE,
                status_code=401,
                reason_code="invalid_code",
            )

        self._repo.mark_consumed(row, now)

    def _generate_code(self) -> str:
        length = max(4, min(10, self._settings.auth_email_code_length))
        return f"{secrets.randbelow(10 ** length):0{length}d}"

    def _now(self) -> datetime:
        return self._now_fn()
