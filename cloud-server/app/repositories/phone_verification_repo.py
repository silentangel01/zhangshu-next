"""Repository for phone verification code lifecycle."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.phone_verification_code import PhoneVerificationCode


class PhoneVerificationCodeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, code: PhoneVerificationCode, *, commit: bool = True
    ) -> PhoneVerificationCode:
        self.db.add(code)
        if commit:
            self.db.commit()
            self.db.refresh(code)
        return code

    def get_latest_active(
        self, phone_number: str, purpose: str, now: datetime
    ) -> PhoneVerificationCode | None:
        return self.db.scalar(
            select(PhoneVerificationCode)
            .where(
                PhoneVerificationCode.phone_number == phone_number,
                PhoneVerificationCode.purpose == purpose,
                PhoneVerificationCode.consumed_at.is_(None),
                PhoneVerificationCode.expires_at >= now,
            )
            .order_by(desc(PhoneVerificationCode.created_at))
            .limit(1)
        )

    def consume_active_for_phone(
        self, phone_number: str, purpose: str, now: datetime, *, commit: bool = True
    ) -> int:
        rows = self.db.scalars(
            select(PhoneVerificationCode).where(
                PhoneVerificationCode.phone_number == phone_number,
                PhoneVerificationCode.purpose == purpose,
                PhoneVerificationCode.consumed_at.is_(None),
            )
        ).all()
        for row in rows:
            row.consumed_at = now
        if commit:
            self.db.commit()
        return len(rows)

    def mark_consumed(
        self, code: PhoneVerificationCode, now: datetime, *, commit: bool = True
    ) -> PhoneVerificationCode:
        code.consumed_at = now
        if commit:
            self.db.commit()
            self.db.refresh(code)
        return code

    def increment_attempts(
        self, code: PhoneVerificationCode, *, commit: bool = True
    ) -> PhoneVerificationCode:
        code.attempt_count = (code.attempt_count or 0) + 1
        if commit:
            self.db.commit()
            self.db.refresh(code)
        return code
