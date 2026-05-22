from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.character import Character
from app.models.clue import Clue
from app.models.outline_item_character import OutlineItemCharacter
from app.models.outline_item_clue import OutlineItemClue
from app.models.outline_item_setting import OutlineItemSetting
from app.models.outline_item_timeline_event import OutlineItemTimelineEvent
from app.models.setting_item import SettingItem
from app.models.timeline_event import TimelineEvent
from app.models.timeline_event_character import TimelineEventCharacter
from app.models.timeline_event_clue import TimelineEventClue
from app.models.timeline_event_setting import TimelineEventSetting


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MaterialLinkRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_timeline_event_characters(self, event_id: str) -> list[TimelineEventCharacter]:
        statement = (
            select(TimelineEventCharacter)
            .join(Character, TimelineEventCharacter.character_id == Character.id)
            .where(
                TimelineEventCharacter.timeline_event_id == event_id,
                Character.deleted_at.is_(None),
            )
            .order_by(TimelineEventCharacter.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def list_timeline_event_settings(self, event_id: str) -> list[TimelineEventSetting]:
        statement = (
            select(TimelineEventSetting)
            .join(SettingItem, TimelineEventSetting.setting_id == SettingItem.id)
            .where(
                TimelineEventSetting.timeline_event_id == event_id,
                SettingItem.deleted_at.is_(None),
            )
            .order_by(TimelineEventSetting.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def list_timeline_event_clues(self, event_id: str) -> list[TimelineEventClue]:
        statement = (
            select(TimelineEventClue)
            .join(Clue, TimelineEventClue.clue_id == Clue.id)
            .where(
                TimelineEventClue.timeline_event_id == event_id,
                Clue.deleted_at.is_(None),
            )
            .order_by(TimelineEventClue.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def list_outline_characters(self, outline_item_id: str) -> list[OutlineItemCharacter]:
        statement = (
            select(OutlineItemCharacter)
            .join(Character, OutlineItemCharacter.character_id == Character.id)
            .where(
                OutlineItemCharacter.outline_item_id == outline_item_id,
                Character.deleted_at.is_(None),
            )
            .order_by(OutlineItemCharacter.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def list_outline_settings(self, outline_item_id: str) -> list[OutlineItemSetting]:
        statement = (
            select(OutlineItemSetting)
            .join(SettingItem, OutlineItemSetting.setting_id == SettingItem.id)
            .where(
                OutlineItemSetting.outline_item_id == outline_item_id,
                SettingItem.deleted_at.is_(None),
            )
            .order_by(OutlineItemSetting.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def list_outline_clues(self, outline_item_id: str) -> list[OutlineItemClue]:
        statement = (
            select(OutlineItemClue)
            .join(Clue, OutlineItemClue.clue_id == Clue.id)
            .where(
                OutlineItemClue.outline_item_id == outline_item_id,
                Clue.deleted_at.is_(None),
            )
            .order_by(OutlineItemClue.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def list_outline_timeline_events(
        self,
        outline_item_id: str,
    ) -> list[OutlineItemTimelineEvent]:
        statement = (
            select(OutlineItemTimelineEvent)
            .join(TimelineEvent, OutlineItemTimelineEvent.timeline_event_id == TimelineEvent.id)
            .where(
                OutlineItemTimelineEvent.outline_item_id == outline_item_id,
                TimelineEvent.deleted_at.is_(None),
            )
            .order_by(OutlineItemTimelineEvent.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def get_existing(
        self,
        model: type[Any],
        source_field: str,
        source_id: str,
        target_field: str,
        target_id: str,
    ) -> Any | None:
        statement = select(model).where(
            getattr(model, source_field) == source_id,
            getattr(model, target_field) == target_id,
        )
        return self.db.scalar(statement)

    def create(self, link: Any) -> Any:
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def update(self, link: Any, values: dict[str, object]) -> Any:
        for field, value in values.items():
            setattr(link, field, value)

        link.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(link)
        return link

    def delete(self, link: Any) -> None:
        self.db.delete(link)
        self.db.commit()

    def count_by_project(self, model: type[Any], project_id: str) -> int:
        statement = select(func.count()).select_from(model).where(model.project_id == project_id)
        return int(self.db.scalar(statement) or 0)
