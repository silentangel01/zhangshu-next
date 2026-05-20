from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.setting_item import SettingItem
from app.repositories.project_repo import ProjectRepository
from app.repositories.setting_repo import SettingRepository
from app.schemas.setting import SettingCreate, SettingUpdate


class SettingNotFoundError(Exception):
    pass


class SettingProjectNotFoundError(Exception):
    pass


class SettingParentNotFoundError(Exception):
    pass


class SettingParentProjectMismatchError(Exception):
    pass


class SettingService:
    def __init__(self, db: Session):
        self.setting_repo = SettingRepository(db)
        self.project_repo = ProjectRepository(db)

    def list_project_settings(
        self,
        project_id: str,
        *,
        item_type: str | None = None,
        canon_status: str | None = None,
        importance: str | None = None,
        keyword: str | None = None,
    ) -> list[SettingItem]:
        self._ensure_project_exists(project_id)
        return self.setting_repo.list_active_by_project(
            project_id,
            item_type=item_type,
            canon_status=canon_status,
            importance=importance,
            keyword=keyword,
        )

    def create_setting(self, project_id: str, data: SettingCreate) -> SettingItem:
        self._ensure_project_exists(project_id)
        self._validate_parent(project_id, data.parent_id)

        setting = SettingItem(
            id=str(uuid4()),
            project_id=project_id,
            parent_id=data.parent_id,
            title=data.title,
            item_type=data.item_type,
            canon_status=data.canon_status,
            summary=data.summary,
            detail=data.detail,
            tags=data.tags,
            order_index=data.order_index,
            importance=data.importance,
        )
        return self.setting_repo.create(setting)

    def get_setting(self, setting_id: str) -> SettingItem:
        setting = self.setting_repo.get_active(setting_id)
        if setting is None:
            raise SettingNotFoundError
        return setting

    def update_setting(self, setting_id: str, data: SettingUpdate) -> SettingItem:
        setting = self.get_setting(setting_id)
        values = data.model_dump(exclude_unset=True)
        if "parent_id" in values:
            parent_id = values["parent_id"]
            if parent_id == setting.id:
                raise SettingParentNotFoundError
            self._validate_parent(setting.project_id, parent_id)
        return self.setting_repo.update(setting, values)

    def delete_setting(self, setting_id: str) -> SettingItem:
        setting = self.get_setting(setting_id)
        return self.setting_repo.soft_delete(setting)

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise SettingProjectNotFoundError

    def _validate_parent(self, project_id: str, parent_id: str | None) -> None:
        if parent_id is None:
            return

        parent = self.setting_repo.get_active(parent_id)
        if parent is None:
            raise SettingParentNotFoundError
        if parent.project_id != project_id:
            raise SettingParentProjectMismatchError
