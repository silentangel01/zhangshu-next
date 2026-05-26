"""Refresh token data access layer."""

from __future__ import annotations

from sqlalchemy import select
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

    def create(
        self, token: RefreshToken, *, commit: bool = True
    ) -> RefreshToken:
        self.db.add(token)
        if commit:
            self.db.commit()
            self.db.refresh(token)
        return token

    def revoke(
        self, token: RefreshToken, *, commit: bool = True
    ) -> RefreshToken:
        token.revoked_at = utc_now()
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
