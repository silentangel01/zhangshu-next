"""Repository for user login identity bindings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth_identity import AuthIdentity


class AuthIdentityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_provider_identifier(
        self, provider: str, identifier: str
    ) -> AuthIdentity | None:
        return self.db.scalar(
            select(AuthIdentity).where(
                AuthIdentity.provider == provider,
                AuthIdentity.identifier == identifier,
            )
        )

    def get_for_user_provider(
        self, user_id: str, provider: str
    ) -> AuthIdentity | None:
        return self.db.scalar(
            select(AuthIdentity).where(
                AuthIdentity.user_id == user_id,
                AuthIdentity.provider == provider,
            )
        )

    def list_for_user(self, user_id: str) -> list[AuthIdentity]:
        return list(
            self.db.scalars(
                select(AuthIdentity).where(AuthIdentity.user_id == user_id)
            ).all()
        )

    def create(self, identity: AuthIdentity, *, commit: bool = True) -> AuthIdentity:
        self.db.add(identity)
        if commit:
            self.db.commit()
            self.db.refresh(identity)
        return identity
