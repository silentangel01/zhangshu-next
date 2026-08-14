"""OAuth login orchestration for WeChat and QQ."""

from __future__ import annotations

import json
import secrets
from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import build_internal_oauth_email, hash_password, sha256_text
from app.infrastructure.oauth_clients import (
    OAuthProviderError,
    OAuthProviderProfile,
    create_oauth_client,
)
from app.models.auth_identity import AuthIdentity
from app.models.oauth_login_session import OAuthLoginSession
from app.models.user import User, utc_now
from app.repositories.auth_identity_repo import AuthIdentityRepository
from app.repositories.oauth_login_session_repo import OAuthLoginSessionRepository
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService

SUPPORTED_OAUTH_PROVIDERS = frozenset({"wechat", "qq"})


class OAuthAuthError(Exception):
    """Raised for OAuth login failures."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class OAuthAuthService:
    def __init__(self, db: Session, settings: Settings | None = None):
        self._db = db
        self._settings = settings or get_settings()
        self._session_repo = OAuthLoginSessionRepository(db)
        self._identity_repo = AuthIdentityRepository(db)
        self._user_repo = UserRepository(db)

    def start_login(
        self,
        provider: str,
        *,
        device_id: str | None = None,
        device_name: str | None = None,
    ) -> dict:
        provider = self._normalize_provider(provider)
        self._ensure_provider_enabled(provider)

        state = secrets.token_urlsafe(32)
        poll_token = secrets.token_urlsafe(32)
        session_id = secrets.token_urlsafe(24)
        now = utc_now()
        expires_at = now + timedelta(seconds=self._settings.oauth_session_ttl_seconds)
        session = OAuthLoginSession(
            id=session_id,
            provider=provider,
            state_hash=sha256_text(state),
            poll_token_hash=sha256_text(poll_token),
            status="pending",
            device_id=device_id,
            device_name=device_name,
            expires_at=expires_at,
            created_at=now,
        )
        self._session_repo.create(session)

        client = create_oauth_client(provider, self._settings)
        authorization_url = client.build_authorization_url(
            state, self._callback_url(provider)
        )
        return {
            "provider": provider,
            "authorization_url": authorization_url,
            "session_id": session_id,
            "poll_token": poll_token,
            "expires_in_seconds": self._settings.oauth_session_ttl_seconds,
        }

    def complete_callback(
        self,
        provider: str,
        *,
        state: str,
        code: str,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> str:
        provider = self._normalize_provider(provider)
        session = self._session_repo.get_by_state_hash(sha256_text(state))
        if session is None or session.provider != provider:
            raise OAuthAuthError("登录会话无效或已过期。", status_code=400)
        if session.expires_at < utc_now() or session.status != "pending":
            raise OAuthAuthError("登录会话无效或已过期。", status_code=400)

        try:
            profile = create_oauth_client(provider, self._settings).fetch_profile(
                code, self._callback_url(provider)
            )
            user = self._get_or_create_user(profile)
            token_payload = AuthService(self._db).issue_tokens_for_user(
                user,
                user_agent=user_agent,
                client_ip=client_ip,
                device_id=session.device_id,
                device_name=session.device_name,
            )
            token_payload["display_name"] = user.display_name
            token_payload["provider"] = provider
            session.status = "completed"
            session.token_payload = json.dumps(token_payload, ensure_ascii=False)
            session.completed_at = utc_now()
            self._db.commit()
        except (OAuthProviderError, OAuthAuthError) as exc:
            session.status = "failed"
            session.error_message = str(exc)
            session.completed_at = utc_now()
            self._db.commit()
            raise OAuthAuthError(str(exc), status_code=400) from exc

        return self._success_html(provider)

    def poll_login(self, session_id: str, poll_token: str) -> dict:
        session = self._session_repo.get_by_id(session_id)
        if session is None or session.poll_token_hash != sha256_text(poll_token):
            raise OAuthAuthError("登录会话无效或已过期。", status_code=404)
        if session.expires_at < utc_now():
            raise OAuthAuthError("登录会话已过期，请重新发起登录。", status_code=410)
        if session.status == "pending":
            return {"status": "pending", "provider": session.provider}
        if session.status == "failed":
            return {
                "status": "failed",
                "provider": session.provider,
                "error_message": session.error_message or "第三方登录失败。",
            }
        if session.consumed_at is not None:
            raise OAuthAuthError("登录结果已被领取，请重新发起登录。", status_code=410)
        if not session.token_payload:
            raise OAuthAuthError("登录结果异常，请重新发起登录。", status_code=500)

        session.consumed_at = utc_now()
        self._db.commit()
        payload = json.loads(session.token_payload)
        payload["status"] = "completed"
        return payload

    def _get_or_create_user(self, profile: OAuthProviderProfile) -> User:
        identity = self._identity_repo.get_by_provider_identifier(
            profile.provider, profile.identifier
        )
        if identity:
            user = self._user_repo.get_by_id(identity.user_id)
            if user and user.is_active and user.deleted_at is None and user.anonymized_at is None:
                return user
            raise OAuthAuthError("账号已不可用，请联系管理员。", status_code=403)

        now = utc_now()
        display_name = profile.display_name.strip()[:128] or self._provider_label(profile.provider)
        user = User(
            id=str(uuid4()),
            email=build_internal_oauth_email(profile.provider, profile.identifier),
            password_hash=hash_password(secrets.token_urlsafe(32)),
            display_name=display_name,
            created_at=now,
            updated_at=now,
        )
        self._user_repo.create(user, commit=False)
        self._identity_repo.create(
            AuthIdentity(
                id=str(uuid4()),
                user_id=user.id,
                provider=profile.provider,
                identifier=profile.identifier,
                verified_at=now,
                created_at=now,
                updated_at=now,
            ),
            commit=False,
        )
        self._db.commit()
        self._db.refresh(user)
        return user

    def _callback_url(self, provider: str) -> str:
        base = self._settings.oauth_public_base_url.rstrip("/")
        if not base:
            raise OAuthAuthError("第三方登录公网回调地址未配置。", status_code=503)
        return f"{base}/api/auth/oauth/{provider}/callback"

    def _ensure_provider_enabled(self, provider: str) -> None:
        if provider == "wechat" and (
            not self._settings.wechat_oauth_enabled
            or not self._settings.wechat_oauth_app_id
            or not self._settings.wechat_oauth_app_secret
        ):
            raise OAuthAuthError("微信登录暂未配置。", status_code=503)
        if provider == "qq" and (
            not self._settings.qq_oauth_enabled
            or not self._settings.qq_oauth_app_id
            or not self._settings.qq_oauth_app_secret
        ):
            raise OAuthAuthError("QQ 登录暂未配置。", status_code=503)

    @staticmethod
    def _normalize_provider(provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized not in SUPPORTED_OAUTH_PROVIDERS:
            raise OAuthAuthError("不支持的登录方式。", status_code=404)
        return normalized

    @staticmethod
    def _provider_label(provider: str) -> str:
        return "微信用户" if provider == "wechat" else "QQ 用户"

    @staticmethod
    def _success_html(provider: str) -> str:
        label = "微信" if provider == "wechat" else "QQ"
        return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <title>{label}登录完成</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 48px; color: #172033; }}
    main {{ max-width: 520px; margin: 0 auto; }}
    h1 {{ font-size: 24px; }}
    p {{ color: #586174; line-height: 1.7; }}
  </style>
</head>
<body>
  <main>
    <h1>{label}登录已完成</h1>
    <p>请回到章枢应用，登录状态会自动更新。这个页面可以关闭。</p>
  </main>
</body>
</html>"""
