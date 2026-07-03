"""Repository for short-lived OAuth login sessions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oauth_login_session import OAuthLoginSession


class OAuthLoginSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, session: OAuthLoginSession, *, commit: bool = True) -> OAuthLoginSession:
        self.db.add(session)
        if commit:
            self.db.commit()
            self.db.refresh(session)
        return session

    def get_by_id(self, session_id: str) -> OAuthLoginSession | None:
        return self.db.scalar(
            select(OAuthLoginSession).where(OAuthLoginSession.id == session_id)
        )

    def get_by_state_hash(self, state_hash: str) -> OAuthLoginSession | None:
        return self.db.scalar(
            select(OAuthLoginSession).where(OAuthLoginSession.state_hash == state_hash)
        )
