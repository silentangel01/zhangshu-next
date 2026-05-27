"""Authentication service: register, login, refresh, me."""

from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    normalize_email,
    validate_password_strength,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User, utc_now
from app.repositories.refresh_token_repo import RefreshTokenRepository
from app.repositories.user_repo import UserRepository
from app.services.token_service import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_jti,
)

logger = logging.getLogger(__name__)

_AUTH_FAILED_MESSAGE = "邮箱或密码错误。"


class AuthError(Exception):
    """Raised for authentication failures."""

    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


class AuthService:
    def __init__(self, db: Session):
        self._db = db
        self._user_repo = UserRepository(db)
        self._token_repo = RefreshTokenRepository(db)

    def register(
        self,
        email: str,
        password: str,
        display_name: str,
        *,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> dict:
        normalized = normalize_email(email)

        pw_error = validate_password_strength(password)
        if pw_error:
            raise AuthError(pw_error, status_code=400)

        if self._user_repo.get_by_email(normalized) is not None:
            raise AuthError("该邮箱已注册。", status_code=400)

        user = User(
            id=str(uuid4()),
            email=normalized,
            password_hash=hash_password(password),
            display_name=display_name.strip() or normalized,
        )
        self._user_repo.create(user)

        return self._issue_tokens(user, user_agent=user_agent, client_ip=client_ip)

    def login(
        self,
        email: str,
        password: str,
        *,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> dict:
        normalized = normalize_email(email)
        user = self._user_repo.get_by_email(normalized)

        if user is None:
            raise AuthError(_AUTH_FAILED_MESSAGE)

        if not user.is_active:
            raise AuthError("账号已被禁用。")

        # Block deleted / anonymized accounts
        if user.deleted_at is not None or user.anonymized_at is not None:
            raise AuthError(_AUTH_FAILED_MESSAGE)

        if not verify_password(password, user.password_hash):
            raise AuthError(_AUTH_FAILED_MESSAGE)

        # Update activity tracking fields
        now = utc_now()
        user.last_login_at = now
        user.last_seen_at = now
        user.login_count = (user.login_count or 0) + 1

        return self._issue_tokens(user, user_agent=user_agent, client_ip=client_ip)

    def refresh(
        self,
        refresh_token_str: str,
        *,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> dict:
        try:
            payload = decode_token(refresh_token_str, "refresh")
        except TokenError as exc:
            raise AuthError(str(exc)) from exc

        jti = payload.get("jti", "")
        jti_h = hash_jti(jti)
        stored = self._token_repo.get_by_jti_hash(jti_h)

        if stored is None:
            raise AuthError("Refresh token 无效。")
        if stored.revoked_at is not None:
            raise AuthError("Refresh token 已被撤销。")
        if stored.expires_at < utc_now():
            raise AuthError("Refresh token 已过期。")

        user = self._user_repo.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise AuthError("用户不存在或已被禁用。")

        if user.deleted_at is not None or user.anonymized_at is not None:
            raise AuthError("账号已被删除。")

        # Update last_used_at on the old token before revoking
        self._token_repo.update(stored, {"last_used_at": utc_now()})

        # Revoke old refresh token with rotation reason
        self._token_repo.revoke(stored, reason="rotated")

        # Issue new tokens
        new_access = create_access_token(user.id)
        new_refresh_str, new_jti, new_expires = create_refresh_token(user.id)
        new_jti_h = hash_jti(new_jti)

        new_rt = RefreshToken(
            id=str(uuid4()),
            user_id=user.id,
            jti_hash=new_jti_h,
            expires_at=new_expires,
            user_agent=user_agent,
            client_ip=client_ip,
        )
        self._token_repo.create(new_rt)

        # Link old to new
        self._token_repo.update(stored, {"replaced_by_id": new_rt.id})

        return {
            "access_token": new_access,
            "refresh_token": new_refresh_str,
            "user_id": user.id,
        }

    def get_me(self, user_id: str) -> dict:
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise AuthError("用户不存在。", status_code=404)
        return {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
        }

    def _issue_tokens(
        self,
        user: User,
        *,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> dict:
        access = create_access_token(user.id)
        refresh_str, jti, expires_at = create_refresh_token(user.id)
        jti_h = hash_jti(jti)

        rt = RefreshToken(
            id=str(uuid4()),
            user_id=user.id,
            jti_hash=jti_h,
            expires_at=expires_at,
            user_agent=user_agent,
            client_ip=client_ip,
        )
        self._token_repo.create(rt)

        return {
            "access_token": access,
            "refresh_token": refresh_str,
            "user_id": user.id,
        }
