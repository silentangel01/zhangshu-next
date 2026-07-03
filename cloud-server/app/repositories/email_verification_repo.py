"""Repository for email verification code lifecycle."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.email_verification_code import EmailVerificationCode


class EmailVerificationCodeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, code: EmailVerificationCode, *, commit: bool = True
    ) -> EmailVerificationCode:
        self.db.add(code)
        if commit:
            self.db.commit()
            self.db.refresh(code)
        return code

    def get_latest_active(
        self, email: str, purpose: str, now: datetime
    ) -> EmailVerificationCode | None:
        return self.db.scalar(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.email == email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.consumed_at.is_(None),
                EmailVerificationCode.expires_at >= now,
            )
            .order_by(desc(EmailVerificationCode.created_at))
            .limit(1)
        )

    def consume_active_for_email(
        self,
        email: str,
        purpose: str,
        now: datetime,
        *,
        commit: bool = True,
    ) -> int:
        rows = self.db.scalars(
            select(EmailVerificationCode).where(
                EmailVerificationCode.email == email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.consumed_at.is_(None),
            )
        ).all()
        for row in rows:
            row.consumed_at = now
        if commit:
            self.db.commit()
        return len(rows)

    def mark_consumed(
        self,
        code: EmailVerificationCode,
        now: datetime,
        *,
        commit: bool = True,
    ) -> EmailVerificationCode:
        code.consumed_at = now
        if commit:
            self.db.commit()
            self.db.refresh(code)
        return code

    def increment_attempts(
        self,
        code: EmailVerificationCode,
        *,
        commit: bool = True,
    ) -> EmailVerificationCode:
        code.attempt_count = (code.attempt_count or 0) + 1
        if commit:
            self.db.commit()
            self.db.refresh(code)
        return code
