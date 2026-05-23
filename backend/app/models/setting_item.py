from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SettingItem(Base):
    __tablename__ = "setting_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("setting_items.id"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    canon_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="", nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    importance: Mapped[str] = mapped_column(String(32), default="normal", nullable=False, index=True)
    node_kind: Mapped[str] = mapped_column(String(16), default="page", nullable=False, index=True)
    folder_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    folder_default_item_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
