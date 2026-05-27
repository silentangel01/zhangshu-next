"""Database-level rate limiting service.

Replaces the in-process ``_rate_limit_store`` dict with a shared
database table so limits work across multiple Uvicorn workers and
Docker containers.

Keys are hashed or sanitised — raw email addresses are never stored.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.security import sha256_text
from app.models.rate_limit_event import RateLimitEvent, utc_now
from app.repositories.rate_limit_repo import RateLimitRepository

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when a rate limit is exceeded."""

    def __init__(self, message: str = "请求过于频繁，请稍后再试。"):
        super().__init__(message)


class RateLimitService:
    """Cross-worker rate limiter backed by the ``rate_limit_events`` table."""

    # Predefined scopes
    AUTH_LOGIN = "auth_login"
    AUTH_REGISTER = "auth_register"
    BACKUP_INIT = "backup_init"
    ACCOUNT_DELETE = "account_delete"
    FEEDBACK_CREATE = "feedback_create"
    FEEDBACK_UPLOAD_INIT = "feedback_upload_init"
    ADMIN_LOGIN = "admin_login"
    PASSWORD_CHANGE = "password_change"

    def __init__(self, db: Session):
        self._db = db
        self._repo = RateLimitRepository(db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_record(
        self,
        scope: str,
        key: str,
        limit: int,
        window_seconds: int,
        *,
        user_id: str | None = None,
        client_ip: str | None = None,
    ) -> None:
        """Check the rate limit and record the event if allowed.

        Raises :class:`RateLimitError` if the limit is exceeded.
        """
        now = utc_now()
        window_start = now - timedelta(seconds=window_seconds)

        count = self._repo.count_active(scope, key, window_start)
        if count >= limit:
            raise RateLimitError()

        event = RateLimitEvent(
            id=str(uuid4()),
            scope=scope,
            key=key,
            user_id=user_id,
            client_ip=client_ip,
            expires_at=now + timedelta(seconds=window_seconds),
        )
        self._repo.create(event)

    def check_login(
        self, client_ip: str, email: str, limit: int, window_seconds: int
    ) -> None:
        """Rate limit for login — keyed by IP + email hash."""
        key = self._make_key(client_ip, sha256_text(email.lower().strip()))
        self.check_and_record(
            self.AUTH_LOGIN, key, limit, window_seconds, client_ip=client_ip
        )

    def check_register(
        self, client_ip: str, email: str, limit: int, window_seconds: int
    ) -> None:
        """Rate limit for registration — keyed by IP + email domain."""
        domain = email.strip().split("@")[-1].lower() if "@" in email else ""
        key = self._make_key(client_ip, domain)
        self.check_and_record(
            self.AUTH_REGISTER, key, limit, window_seconds, client_ip=client_ip
        )

    def check_backup_init(
        self, user_id: str, limit: int, window_seconds: int, client_ip: str = ""
    ) -> None:
        """Rate limit for backup init — keyed by user_id."""
        self.check_and_record(
            self.BACKUP_INIT, user_id, limit, window_seconds,
            user_id=user_id, client_ip=client_ip,
        )

    def check_account_delete(
        self, user_id: str, limit: int, window_seconds: int, client_ip: str = ""
    ) -> None:
        """Rate limit for account deletion — keyed by user_id."""
        self.check_and_record(
            self.ACCOUNT_DELETE, user_id, limit, window_seconds,
            user_id=user_id, client_ip=client_ip,
        )

    def check_feedback_create(
        self,
        limit: int,
        window_seconds: int,
        *,
        user_id: str | None = None,
        client_ip: str = "",
    ) -> None:
        """Rate limit for feedback creation — keyed by user_id or IP."""
        key = user_id or self._make_key(client_ip, "feedback")
        self.check_and_record(
            self.FEEDBACK_CREATE, key, limit, window_seconds,
            user_id=user_id, client_ip=client_ip,
        )

    def check_feedback_upload(
        self,
        limit: int,
        window_seconds: int,
        *,
        user_id: str | None = None,
        client_ip: str = "",
    ) -> None:
        """Rate limit for feedback attachment upload — keyed by user_id or IP."""
        key = user_id or self._make_key(client_ip, "fb_upload")
        self.check_and_record(
            self.FEEDBACK_UPLOAD_INIT, key, limit, window_seconds,
            user_id=user_id, client_ip=client_ip,
        )

    def check_admin_login(
        self, client_ip: str, email: str, limit: int, window_seconds: int
    ) -> None:
        """Rate limit for admin login — keyed by IP + email hash."""
        key = self._make_key(client_ip, sha256_text(email.lower().strip()))
        self.check_and_record(
            self.ADMIN_LOGIN, key, limit, window_seconds, client_ip=client_ip
        )

    def check_password_change(
        self, user_id: str, limit: int, window_seconds: int, client_ip: str = ""
    ) -> None:
        """Rate limit for password change — keyed by user_id."""
        self.check_and_record(
            self.PASSWORD_CHANGE, user_id, limit, window_seconds,
            user_id=user_id, client_ip=client_ip,
        )

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def purge_expired(self) -> int:
        """Remove expired rate limit events. Call periodically or via cron."""
        return self._repo.purge_expired()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(*parts: str) -> str:
        """Combine parts into a short hashed key (never raw email)."""
        return sha256_text(":".join(parts))[:32]
