"""Repository for app_config key-value store."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_config import AppConfig


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AppConfigRepository:
    """Manages persistence of app-level configuration entries."""

    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str) -> AppConfig | None:
        """Return the config entry for a key, or None."""
        return self.db.scalar(
            select(AppConfig).where(AppConfig.config_key == key)
        )

    def get_all(self) -> list[AppConfig]:
        """Return all config entries."""
        return list(self.db.scalars(select(AppConfig)).all())

    def upsert(
        self, key: str, value: str, is_encrypted: bool = False
    ) -> AppConfig:
        """Create or update a config entry."""
        existing = self.get(key)
        now = utc_now()
        if existing:
            existing.config_value = value
            existing.is_encrypted = is_encrypted
            existing.updated_at = now
            self.db.commit()
            self.db.refresh(existing)
            return existing
        entry = AppConfig(
            config_key=key,
            config_value=value,
            is_encrypted=is_encrypted,
            updated_at=now,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def apply_batch(
        self,
        values: dict[str, tuple[str, bool]],
        delete_keys: set[str] | None = None,
    ) -> None:
        """Apply multiple config changes in one transaction.

        Authentication credentials are a logical unit.  Persisting the access
        and refresh token in separate commits can leave an unusable token pair
        behind when the process is interrupted halfway through a refresh.
        """
        now = utc_now()
        delete_keys = delete_keys or set()
        try:
            for key, (value, is_encrypted) in values.items():
                existing = self.get(key)
                if existing is None:
                    self.db.add(
                        AppConfig(
                            config_key=key,
                            config_value=value,
                            is_encrypted=is_encrypted,
                            updated_at=now,
                        )
                    )
                else:
                    existing.config_value = value
                    existing.is_encrypted = is_encrypted
                    existing.updated_at = now

            for key in delete_keys - set(values):
                existing = self.get(key)
                if existing is not None:
                    self.db.delete(existing)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def delete(self, key: str) -> bool:
        """Delete a config entry. Returns True if deleted."""
        existing = self.get(key)
        if existing is None:
            return False
        self.db.delete(existing)
        self.db.commit()
        return True
