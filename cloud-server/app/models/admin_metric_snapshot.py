"""Admin metric snapshot ORM model.

Stores pre-computed dashboard statistics keyed by ``key``. Each snapshot
has a TTL — callers decide whether to return the cached payload or
recompute. Used together with Redis lock to avoid thundering-herd
refreshes across multiple workers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_CST = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    return datetime.now(_CST).replace(tzinfo=None)


class AdminMetricSnapshot(Base):
    __tablename__ = "admin_metric_snapshots"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )
