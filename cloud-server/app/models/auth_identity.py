"""External/login identity bindings for cloud users."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utc_now


class AuthIdentity(Base):
    """A unique login identity bound to one user.

    ``provider`` is intentionally open-ended: email, phone, wechat, qq, etc.
    """

    __tablename__ = "user_auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "identifier", name="uq_auth_identity_provider_identifier"),
        UniqueConstraint("user_id", "provider", name="uq_auth_identity_user_provider"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
