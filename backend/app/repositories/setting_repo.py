from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.setting_item import SettingItem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SettingRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project(
        self,
        project_id: str,
        *,
        item_type: str | None = None,
        canon_status: str | None = None,
        importance: str | None = None,
        keyword: str | None = None,
    ) -> list[SettingItem]:
        statement = select(SettingItem).where(
            SettingItem.project_id == project_id,
            SettingItem.deleted_at.is_(None),
        )

        if item_type is not None:
            statement = statement.where(SettingItem.item_type == item_type)
        if canon_status is not None:
            statement = statement.where(SettingItem.canon_status == canon_status)
        if importance is not None:
            statement = statement.where(SettingItem.importance == importance)
        if keyword:
            pattern = f"%{keyword}%"
            statement = statement.where(
                or_(
                    SettingItem.title.ilike(pattern),
                    SettingItem.summary.ilike(pattern),
                    SettingItem.detail.ilike(pattern),
                    SettingItem.tags.ilike(pattern),
                )
            )

        statement = statement.order_by(
            SettingItem.order_index.asc(),
            SettingItem.updated_at.desc(),
            SettingItem.created_at.desc(),
        )
        return list(self.db.scalars(statement).all())

    def get_active(self, setting_id: str) -> SettingItem | None:
        statement = select(SettingItem).where(
            SettingItem.id == setting_id,
            SettingItem.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create(self, setting: SettingItem) -> SettingItem:
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def update(self, setting: SettingItem, values: dict[str, object]) -> SettingItem:
        for field, value in values.items():
            setattr(setting, field, value)

        setting.updated_at = utc_now()
        setting.version += 1
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def soft_delete(self, setting: SettingItem) -> SettingItem:
        now = utc_now()
        setting.deleted_at = now
        setting.updated_at = now
        setting.version += 1
        self.db.commit()
        self.db.refresh(setting)
        return setting
