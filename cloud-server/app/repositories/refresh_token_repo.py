"""Refresh token data access layer."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
from app.models.user import utc_now


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_jti_hash(self, jti_hash: str) -> RefreshToken | None:
        return self.db.scalar(
            select(RefreshToken).where(RefreshToken.jti_hash == jti_hash)
        )

    def has_active_session(self, user_id: str, session_id: str) -> bool:
        return self.db.scalar(
            select(RefreshToken.id).where(
                RefreshToken.user_id == user_id,
                RefreshToken.session_id == session_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > utc_now(),
            ).limit(1)
        ) is not None

    def revoke_session(
        self, user_id: str, session_id: str, *, reason: str
    ) -> int:
        result = self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.session_id == session_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=utc_now(), revoked_reason=reason)
        )
        self.db.commit()
        return int(result.rowcount or 0)

    def create(
        self, token: RefreshToken, *, commit: bool = True
    ) -> RefreshToken:
        self.db.add(token)
        if commit:
            self.db.commit()
            self.db.refresh(token)
        return token

    def revoke(
        self, token: RefreshToken, *, reason: str | None = None, commit: bool = True
    ) -> RefreshToken:
        token.revoked_at = utc_now()
        if reason:
            token.revoked_reason = reason
        if commit:
            self.db.commit()
            self.db.refresh(token)
        return token

    def update(
        self, token: RefreshToken, values: dict, *, commit: bool = True
    ) -> RefreshToken:
        for key, value in values.items():
            setattr(token, key, value)
        if commit:
            self.db.commit()
            self.db.refresh(token)
        return token
