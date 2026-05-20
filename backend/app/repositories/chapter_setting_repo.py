from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chapter_setting import ChapterSetting
from app.models.setting_item import SettingItem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChapterSettingRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_chapter(self, chapter_id: str) -> list[tuple[ChapterSetting, SettingItem]]:
        statement = (
            select(ChapterSetting, SettingItem)
            .join(SettingItem, ChapterSetting.setting_item_id == SettingItem.id)
            .where(
                ChapterSetting.chapter_id == chapter_id,
                SettingItem.deleted_at.is_(None),
            )
            .order_by(
                SettingItem.order_index.asc(),
                ChapterSetting.created_at.asc(),
            )
        )
        return list(self.db.execute(statement).all())

    def get(self, link_id: str) -> ChapterSetting | None:
        statement = select(ChapterSetting).where(ChapterSetting.id == link_id)
        return self.db.scalar(statement)

    def create(self, link: ChapterSetting) -> ChapterSetting:
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def update(self, link: ChapterSetting, values: dict[str, object]) -> ChapterSetting:
        for field, value in values.items():
            setattr(link, field, value)

        link.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(link)
        return link

    def delete(self, link: ChapterSetting) -> None:
        self.db.delete(link)
        self.db.commit()
