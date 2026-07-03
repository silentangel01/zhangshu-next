"""Phone verification code service for auth and binding flows."""

from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta
from typing import Callable, Literal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import normalize_phone_number, sha256_text
from app.infrastructure.sms_sender import SmsDeliveryError, SmsSender
from app.models.phone_verification_code import PhoneVerificationCode
from app.models.user import utc_now
from app.repositories.auth_identity_repo import AuthIdentityRepository
from app.repositories.phone_verification_repo import PhoneVerificationCodeRepository

PhoneCodePurpose = Literal["register", "login", "bind"]

_INVALID_CODE_MESSAGE = "验证码错误或已过期。"


class PhoneVerificationError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        reason_code: str = "phone_verification_failed",
    ):
        super().__init__(message)
        self.status_code = status_code
        self.reason_code = reason_code


def hash_phone_code(phone_number: str, purpose: str, code: str, secret: str) -> str:
    normalized = normalize_phone_number(phone_number)
    return sha256_text(f"{secret}:{purpose}:{normalized}:{code.strip()}")


class PhoneVerificationService:
    def __init__(
        self,
        db: Session,
        *,
        sender: SmsSender | None = None,
        settings: Settings | None = None,
        now_fn: Callable[[], datetime] = utc_now,
    ):
        self._db = db
        self._settings = settings or get_settings()
        self._sender = sender or SmsSender(self._settings)
        self._repo = PhoneVerificationCodeRepository(db)
        self._identity_repo = AuthIdentityRepository(db)
        self._now_fn = now_fn

    def send_code(self, phone_number: str, purpose: PhoneCodePurpose) -> dict:
        if not self._settings.phone_auth_enabled:
            raise PhoneVerificationError(
                "手机号登录暂未启用。",
                status_code=503,
                reason_code="phone_auth_disabled",
            )

        normalized = normalize_phone_number(phone_number)
        now = self._now()
        identity = self._identity_repo.get_by_provider_identifier("phone", normalized)

        if purpose in {"register", "bind"} and identity is not None:
            raise PhoneVerificationError(
                "该手机号已绑定其他账号。",
                status_code=400,
                reason_code="phone_registered",
            )

        expires_in = self._settings.auth_phone_code_ttl_seconds
        cooldown = self._settings.auth_phone_code_resend_cooldown_seconds

        if purpose == "login" and identity is None:
            return {
                "ok": True,
                "expires_in_seconds": expires_in,
                "cooldown_seconds": cooldown,
            }

        latest = self._repo.get_latest_active(normalized, purpose, now)
        if latest is not None:
            next_allowed_at = latest.last_sent_at + timedelta(seconds=cooldown)
            if next_allowed_at > now:
                raise PhoneVerificationError(
                    "验证码发送过于频繁，请稍后再试。",
                    status_code=429,
                    reason_code="cooldown",
                )

        code = self._generate_code()
        code_hash = hash_phone_code(
            normalized,
            purpose,
            code,
            self._settings.auth_phone_code_secret or self._settings.jwt_secret_key,
        )
        expires_at = now + timedelta(seconds=expires_in)
        self._repo.consume_active_for_phone(normalized, purpose, now, commit=False)
        row = PhoneVerificationCode(
            id=str(uuid4()),
            phone_number=normalized,
            purpose=purpose,
            code_hash=code_hash,
            expires_at=expires_at,
            attempt_count=0,
            max_attempts=self._settings.auth_phone_code_max_attempts,
            last_sent_at=now,
            created_at=now,
        )
        self._repo.create(row)

        try:
            self._sender.send_verification_code(
                normalized, code, purpose, max(1, expires_in // 60)
            )
        except SmsDeliveryError as exc:
            self._repo.mark_consumed(row, self._now())
            raise PhoneVerificationError(
                str(exc),
                status_code=503,
                reason_code="sms_delivery_failed",
            ) from exc

        return {
            "ok": True,
            "expires_in_seconds": expires_in,
            "cooldown_seconds": cooldown,
        }

    def verify_code(self, phone_number: str, purpose: PhoneCodePurpose, code: str) -> None:
        normalized = normalize_phone_number(phone_number)
        candidate = code.strip()
        if not candidate.isdigit():
            raise PhoneVerificationError(
                _INVALID_CODE_MESSAGE,
                status_code=401,
                reason_code="invalid_code",
            )

        now = self._now()
        row = self._repo.get_latest_active(normalized, purpose, now)
        if row is None:
            raise PhoneVerificationError(
                _INVALID_CODE_MESSAGE,
                status_code=401,
                reason_code="missing_or_expired",
            )

        if row.attempt_count >= row.max_attempts:
            self._repo.mark_consumed(row, now)
            raise PhoneVerificationError(
                _INVALID_CODE_MESSAGE,
                status_code=401,
                reason_code="max_attempts",
            )

        expected = hash_phone_code(
            normalized,
            purpose,
            candidate,
            self._settings.auth_phone_code_secret or self._settings.jwt_secret_key,
        )
        if not hmac.compare_digest(expected, row.code_hash):
            self._repo.increment_attempts(row, commit=False)
            if row.attempt_count >= row.max_attempts:
                row.consumed_at = now
            self._db.commit()
            raise PhoneVerificationError(
                _INVALID_CODE_MESSAGE,
                status_code=401,
                reason_code="invalid_code",
            )

        self._repo.mark_consumed(row, now)

    def _generate_code(self) -> str:
        length = max(4, min(10, self._settings.auth_phone_code_length))
        return f"{secrets.randbelow(10 ** length):0{length}d}"

    def _now(self) -> datetime:
        return self._now_fn()
