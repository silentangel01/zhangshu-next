from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clue_setting import ClueSetting
from app.models.setting_item import SettingItem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ClueSettingRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_clue(self, clue_id: str) -> list[tuple[ClueSetting, SettingItem]]:
        statement = (
            select(ClueSetting, SettingItem)
            .join(SettingItem, ClueSetting.setting_item_id == SettingItem.id)
            .where(ClueSetting.clue_id == clue_id, SettingItem.deleted_at.is_(None))
            .order_by(ClueSetting.created_at.asc())
        )
        return list(self.db.execute(statement).all())

    def get(self, link_id: str) -> ClueSetting | None:
        return self.db.scalar(select(ClueSetting).where(ClueSetting.id == link_id))

    def create(self, link: ClueSetting) -> ClueSetting:
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def update(self, link: ClueSetting, values: dict[str, object]) -> ClueSetting:
        for field, value in values.items():
            setattr(link, field, value)
        link.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(link)
        return link

    def delete(self, link: ClueSetting) -> None:
        self.db.delete(link)
        self.db.commit()
