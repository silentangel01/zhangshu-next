"""App-level configuration key-value store model."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AppConfig(Base):
    """Generic app configuration entry.

    One row per config key. Sensitive values are stored encrypted;
    the is_encrypted flag marks them for decryption on read.
    """

    __tablename__ = "app_config"

    config_key: Mapped[str] = mapped_column(
        String(128), primary_key=True, index=True
    )
    config_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_encrypted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
