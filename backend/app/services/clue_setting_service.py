from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.clue_setting import ClueSetting
from app.repositories.clue_repo import ClueRepository
from app.repositories.clue_setting_repo import ClueSettingRepository
from app.repositories.setting_repo import SettingRepository
from app.schemas.clue import ClueSettingCreate, ClueSettingUpdate


class ClueSettingLinkNotFoundError(Exception):
    pass


class ClueSettingClueNotFoundError(Exception):
    pass


class ClueSettingItemNotFoundError(Exception):
    pass


class ClueSettingProjectMismatchError(Exception):
    pass


class ClueSettingService:
    def __init__(self, db: Session):
        self.db = db
        self.link_repo = ClueSettingRepository(db)
        self.clue_repo = ClueRepository(db)
        self.setting_repo = SettingRepository(db)

    def list_clue_settings(self, clue_id: str) -> list[dict[str, object]]:
        clue = self.clue_repo.get_active(clue_id)
        if clue is None:
            raise ClueSettingClueNotFoundError
        return [self._to_read_payload(link, setting) for link, setting in self.link_repo.list_active_by_clue(clue_id)]

    def add_clue_setting(self, clue_id: str, data: ClueSettingCreate) -> dict[str, object]:
        clue = self.clue_repo.get_active(clue_id)
        if clue is None:
            raise ClueSettingClueNotFoundError
        setting = self.setting_repo.get_active(data.setting_item_id)
        if setting is None:
            raise ClueSettingItemNotFoundError
        if setting.project_id != clue.project_id:
            raise ClueSettingProjectMismatchError
        link = ClueSetting(
            id=str(uuid4()),
            project_id=clue.project_id,
            clue_id=clue.id,
            setting_item_id=setting.id,
            relation_type=data.relation_type,
            note=data.note,
        )
        created = self.link_repo.create(link)
        self._mark_dirty(clue.project_id, created.id, "upsert")
        return self._to_read_payload(created, setting)

    def update_clue_setting(self, link_id: str, data: ClueSettingUpdate) -> dict[str, object]:
        link = self.link_repo.get(link_id)
        if link is None:
            raise ClueSettingLinkNotFoundError
        updated = self.link_repo.update(link, data.model_dump(exclude_unset=True))
        self._mark_dirty(link.project_id, link.id, "upsert")
        setting = self.setting_repo.get_active(updated.setting_item_id)
        if setting is None:
            raise ClueSettingItemNotFoundError
        return self._to_read_payload(updated, setting)

    def delete_clue_setting(self, link_id: str) -> None:
        link = self.link_repo.get(link_id)
        if link is None:
            raise ClueSettingLinkNotFoundError
        deleted = self.link_repo.delete(link)
        self._mark_dirty(link.project_id, deleted.id, "delete")

    def _mark_dirty(self, project_id: str, entity_id: str, action: str) -> None:
        """Mark a clue_setting as dirty for cloud sync (best-effort, never raises)."""
        try:
            from app.services.sync_dirty_service import SyncDirtyService

            SyncDirtyService(self.db).mark_dirty(project_id, "clue_settings", entity_id, action)
        except Exception:
            pass

    def _to_read_payload(self, link: ClueSetting, setting) -> dict[str, object]:
        return {
            "id": link.id,
            "project_id": link.project_id,
            "clue_id": link.clue_id,
            "setting_item_id": link.setting_item_id,
            "relation_type": link.relation_type,
            "note": link.note,
            "created_at": link.created_at,
            "updated_at": link.updated_at,
            "setting": setting,
        }
