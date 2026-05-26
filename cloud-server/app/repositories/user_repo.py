"""User data access layer."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.scalar(select(User).where(User.id == user_id))

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def create(self, user: User, *, commit: bool = True) -> User:
        self.db.add(user)
        if commit:
            self.db.commit()
            self.db.refresh(user)
        return user

    def update(
        self, user: User, values: dict, *, commit: bool = True
    ) -> User:
        for key, value in values.items():
            setattr(user, key, value)
        if commit:
            self.db.commit()
            self.db.refresh(user)
        return user
