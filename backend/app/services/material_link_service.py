from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.character import Character
from app.models.clue import Clue
from app.models.outline_item import OutlineItem
from app.models.outline_item_character import OutlineItemCharacter
from app.models.outline_item_clue import OutlineItemClue
from app.models.outline_item_setting import OutlineItemSetting
from app.models.outline_item_timeline_event import OutlineItemTimelineEvent
from app.models.project import Project
from app.models.setting_item import SettingItem
from app.models.timeline_event import TimelineEvent
from app.models.timeline_event_character import TimelineEventCharacter
from app.models.timeline_event_clue import TimelineEventClue
from app.models.timeline_event_setting import TimelineEventSetting
from app.repositories.material_link_repo import MaterialLinkRepository
from app.schemas.material_links import (
    OutlineCharacterLinkCreate,
    OutlineClueLinkCreate,
    OutlineSettingLinkCreate,
    OutlineTimelineEventLinkCreate,
    TimelineEventCharacterLinkCreate,
    TimelineEventClueLinkCreate,
    TimelineEventSettingLinkCreate,
)


class MaterialLinkSourceNotFoundError(Exception):
    pass


class MaterialLinkTargetNotFoundError(Exception):
    pass


class MaterialLinkNotFoundError(Exception):
    pass


class MaterialLinkProjectMismatchError(Exception):
    pass


class MaterialLinkProjectNotFoundError(Exception):
    pass


class MaterialLinkService:
    # Map model classes to sync entity type strings
    _ENTITY_TYPE_MAP: dict[type, str] = {
        TimelineEventCharacter: "timeline_event_characters",
        TimelineEventSetting: "timeline_event_settings",
        TimelineEventClue: "timeline_event_clues",
        OutlineItemCharacter: "outline_item_characters",
        OutlineItemSetting: "outline_item_settings",
        OutlineItemClue: "outline_item_clues",
        OutlineItemTimelineEvent: "outline_item_timeline_events",
    }

    def __init__(self, db: Session):
        self.db = db
        self.repo = MaterialLinkRepository(db)

    def list_timeline_event_characters(self, event_id: str) -> list[TimelineEventCharacter]:
        self._get_timeline_event(event_id)
        return self.repo.list_timeline_event_characters(event_id)

    def add_timeline_event_character(
        self,
        event_id: str,
        data: TimelineEventCharacterLinkCreate,
    ) -> TimelineEventCharacter:
        event = self._get_timeline_event(event_id)
        character = self._get_character(data.character_id)
        self._ensure_same_project(event.project_id, character.project_id)
        return self._upsert_link(
            TimelineEventCharacter,
            "timeline_event_id",
            event.id,
            "character_id",
            character.id,
            event.project_id,
            data.relation_type,
            data.note,
        )

    def delete_timeline_event_character(self, event_id: str, character_id: str) -> None:
        self._delete_link(TimelineEventCharacter, "timeline_event_id", event_id, "character_id", character_id)

    def list_timeline_event_settings(self, event_id: str) -> list[TimelineEventSetting]:
        self._get_timeline_event(event_id)
        return self.repo.list_timeline_event_settings(event_id)

    def add_timeline_event_setting(
        self,
        event_id: str,
        data: TimelineEventSettingLinkCreate,
    ) -> TimelineEventSetting:
        event = self._get_timeline_event(event_id)
        setting = self._get_setting(data.setting_id)
        self._ensure_same_project(event.project_id, setting.project_id)
        return self._upsert_link(
            TimelineEventSetting,
            "timeline_event_id",
            event.id,
            "setting_id",
            setting.id,
            event.project_id,
            data.relation_type,
            data.note,
        )

    def delete_timeline_event_setting(self, event_id: str, setting_id: str) -> None:
        self._delete_link(TimelineEventSetting, "timeline_event_id", event_id, "setting_id", setting_id)

    def list_timeline_event_clues(self, event_id: str) -> list[TimelineEventClue]:
        self._get_timeline_event(event_id)
        return self.repo.list_timeline_event_clues(event_id)

    def add_timeline_event_clue(
        self,
        event_id: str,
        data: TimelineEventClueLinkCreate,
    ) -> TimelineEventClue:
        event = self._get_timeline_event(event_id)
        clue = self._get_clue(data.clue_id)
        self._ensure_same_project(event.project_id, clue.project_id)
        return self._upsert_link(
            TimelineEventClue,
            "timeline_event_id",
            event.id,
            "clue_id",
            clue.id,
            event.project_id,
            data.relation_type,
            data.note,
        )

    def delete_timeline_event_clue(self, event_id: str, clue_id: str) -> None:
        self._delete_link(TimelineEventClue, "timeline_event_id", event_id, "clue_id", clue_id)

    def list_outline_characters(self, outline_item_id: str) -> list[OutlineItemCharacter]:
        self._get_outline_item(outline_item_id)
        return self.repo.list_outline_characters(outline_item_id)

    def add_outline_character(
        self,
        outline_item_id: str,
        data: OutlineCharacterLinkCreate,
    ) -> OutlineItemCharacter:
        outline = self._get_outline_item(outline_item_id)
        character = self._get_character(data.character_id)
        self._ensure_same_project(outline.project_id, character.project_id)
        return self._upsert_link(
            OutlineItemCharacter,
            "outline_item_id",
            outline.id,
            "character_id",
            character.id,
            outline.project_id,
            data.relation_type,
            data.note,
        )

    def delete_outline_character(self, outline_item_id: str, character_id: str) -> None:
        self._delete_link(OutlineItemCharacter, "outline_item_id", outline_item_id, "character_id", character_id)

    def list_outline_settings(self, outline_item_id: str) -> list[OutlineItemSetting]:
        self._get_outline_item(outline_item_id)
        return self.repo.list_outline_settings(outline_item_id)

    def add_outline_setting(
        self,
        outline_item_id: str,
        data: OutlineSettingLinkCreate,
    ) -> OutlineItemSetting:
        outline = self._get_outline_item(outline_item_id)
        setting = self._get_setting(data.setting_id)
        self._ensure_same_project(outline.project_id, setting.project_id)
        return self._upsert_link(
            OutlineItemSetting,
            "outline_item_id",
            outline.id,
            "setting_id",
            setting.id,
            outline.project_id,
            data.relation_type,
            data.note,
        )

    def delete_outline_setting(self, outline_item_id: str, setting_id: str) -> None:
        self._delete_link(OutlineItemSetting, "outline_item_id", outline_item_id, "setting_id", setting_id)

    def list_outline_clues(self, outline_item_id: str) -> list[OutlineItemClue]:
        self._get_outline_item(outline_item_id)
        return self.repo.list_outline_clues(outline_item_id)

    def add_outline_clue(
        self,
        outline_item_id: str,
        data: OutlineClueLinkCreate,
    ) -> OutlineItemClue:
        outline = self._get_outline_item(outline_item_id)
        clue = self._get_clue(data.clue_id)
        self._ensure_same_project(outline.project_id, clue.project_id)
        return self._upsert_link(
            OutlineItemClue,
            "outline_item_id",
            outline.id,
            "clue_id",
            clue.id,
            outline.project_id,
            data.relation_type,
            data.note,
        )

    def delete_outline_clue(self, outline_item_id: str, clue_id: str) -> None:
        self._delete_link(OutlineItemClue, "outline_item_id", outline_item_id, "clue_id", clue_id)

    def list_outline_timeline_events(
        self,
        outline_item_id: str,
    ) -> list[OutlineItemTimelineEvent]:
        self._get_outline_item(outline_item_id)
        return self.repo.list_outline_timeline_events(outline_item_id)

    def add_outline_timeline_event(
        self,
        outline_item_id: str,
        data: OutlineTimelineEventLinkCreate,
    ) -> OutlineItemTimelineEvent:
        outline = self._get_outline_item(outline_item_id)
        event = self._get_timeline_event(data.timeline_event_id)
        self._ensure_same_project(outline.project_id, event.project_id)
        return self._upsert_link(
            OutlineItemTimelineEvent,
            "outline_item_id",
            outline.id,
            "timeline_event_id",
            event.id,
            outline.project_id,
            data.relation_type,
            data.note,
        )

    def delete_outline_timeline_event(self, outline_item_id: str, event_id: str) -> None:
        self._delete_link(OutlineItemTimelineEvent, "outline_item_id", outline_item_id, "timeline_event_id", event_id)

    def get_project_summary(self, project_id: str) -> dict[str, int]:
        project = self.db.scalar(
            select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
        )
        if project is None:
            raise MaterialLinkProjectNotFoundError

        return {
            "timeline_event_character_count": self.repo.count_by_project(
                TimelineEventCharacter,
                project_id,
            ),
            "timeline_event_setting_count": self.repo.count_by_project(
                TimelineEventSetting,
                project_id,
            ),
            "timeline_event_clue_count": self.repo.count_by_project(
                TimelineEventClue,
                project_id,
            ),
            "outline_character_count": self.repo.count_by_project(
                OutlineItemCharacter,
                project_id,
            ),
            "outline_setting_count": self.repo.count_by_project(
                OutlineItemSetting,
                project_id,
            ),
            "outline_clue_count": self.repo.count_by_project(
                OutlineItemClue,
                project_id,
            ),
            "outline_timeline_event_count": self.repo.count_by_project(
                OutlineItemTimelineEvent,
                project_id,
            ),
        }

    def _upsert_link(
        self,
        model: type[Any],
        source_field: str,
        source_id: str,
        target_field: str,
        target_id: str,
        project_id: str,
        relation_type: str,
        note: str,
    ) -> Any:
        # Check for active link first
        existing = self.repo.get_existing(model, source_field, source_id, target_field, target_id)
        if existing is not None:
            result = self.repo.update(existing, {"relation_type": relation_type, "note": note})
            self._mark_dirty(model, project_id, result.id, "upsert")
            return result

        # Check for soft-deleted link with same natural key
        deleted = self.repo.get_existing(
            model, source_field, source_id, target_field, target_id,
            include_deleted=True,
        )
        if deleted is not None and deleted.deleted_at is not None:
            result = self.repo.revive(
                deleted,
                {"relation_type": relation_type, "note": note},
            )
            self._mark_dirty(model, project_id, result.id, "upsert")
            return result

        link = model(
            id=str(uuid4()),
            project_id=project_id,
            **{
                source_field: source_id,
                target_field: target_id,
                "relation_type": relation_type,
                "note": note,
            },
        )
        created = self.repo.create(link)
        self._mark_dirty(model, project_id, created.id, "upsert")
        return created

    def _delete_link(
        self,
        model: type[Any],
        source_field: str,
        source_id: str,
        target_field: str,
        target_id: str,
    ) -> None:
        link = self.repo.get_existing(model, source_field, source_id, target_field, target_id)
        if link is None:
            raise MaterialLinkNotFoundError
        deleted = self.repo.delete(link)
        self._mark_dirty(model, link.project_id, deleted.id, "delete")

    def _mark_dirty(self, model: type, project_id: str, entity_id: str, action: str) -> None:
        """Mark a material link as dirty for cloud sync (best-effort, never raises)."""
        entity_type = self._ENTITY_TYPE_MAP.get(model)
        if entity_type is None:
            return
        try:
            from app.services.sync_dirty_service import SyncDirtyService

            SyncDirtyService(self.db).mark_dirty(project_id, entity_type, entity_id, action)
        except Exception:
            pass

    def _get_timeline_event(self, event_id: str) -> TimelineEvent:
        event = self.db.scalar(
            select(TimelineEvent).where(
                TimelineEvent.id == event_id,
                TimelineEvent.deleted_at.is_(None),
            )
        )
        if event is None:
            raise MaterialLinkSourceNotFoundError
        return event

    def _get_outline_item(self, outline_item_id: str) -> OutlineItem:
        outline = self.db.scalar(
            select(OutlineItem).where(
                OutlineItem.id == outline_item_id,
                OutlineItem.deleted_at.is_(None),
            )
        )
        if outline is None:
            raise MaterialLinkSourceNotFoundError
        return outline

    def _get_character(self, character_id: str) -> Character:
        character = self.db.scalar(
            select(Character).where(Character.id == character_id, Character.deleted_at.is_(None))
        )
        if character is None:
            raise MaterialLinkTargetNotFoundError
        return character

    def _get_setting(self, setting_id: str) -> SettingItem:
        setting = self.db.scalar(
            select(SettingItem).where(SettingItem.id == setting_id, SettingItem.deleted_at.is_(None))
        )
        if setting is None:
            raise MaterialLinkTargetNotFoundError
        return setting

    def _get_clue(self, clue_id: str) -> Clue:
        clue = self.db.scalar(select(Clue).where(Clue.id == clue_id, Clue.deleted_at.is_(None)))
        if clue is None:
            raise MaterialLinkTargetNotFoundError
        return clue

    def _ensure_same_project(self, source_project_id: str, target_project_id: str) -> None:
        if source_project_id != target_project_id:
            raise MaterialLinkProjectMismatchError
