from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.setting_item import SettingItem
from app.repositories.project_repo import ProjectRepository
from app.repositories.setting_repo import SettingRepository
from app.schemas.setting import SettingCreate, SettingUpdate


# --- Exceptions ---


class SettingNotFoundError(Exception):
    pass


class SettingProjectNotFoundError(Exception):
    pass


class SettingParentNotFoundError(Exception):
    pass


class SettingParentProjectMismatchError(Exception):
    pass


class SettingInvalidNodeKindError(Exception):
    pass


class SettingInvalidParentError(Exception):
    pass


class SettingParentCycleError(Exception):
    pass


class SettingSystemFolderProtectedError(Exception):
    pass


class SettingFolderNotEmptyError(Exception):
    pass


# --- System folder constants ---


ROOT_FOLDER = {
    "folder_key": "root",
    "title": "全书设定",
    "folder_default_item_type": None,
    "item_type": "custom",
    "is_system": True,
}

DEFAULT_FOLDERS = [
    {"folder_key": "characters", "title": "人物", "folder_default_item_type": "character"},
    {"folder_key": "power", "title": "战力", "folder_default_item_type": "power_system"},
    {"folder_key": "world", "title": "世界观", "folder_default_item_type": "world"},
    {"folder_key": "history", "title": "历史", "folder_default_item_type": "history"},
]


# --- Service ---


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
        node_kind: str | None = None,
    ) -> list[SettingItem]:
        self._ensure_project_exists(project_id)
        self._ensure_default_setting_folders(project_id)
        return self.setting_repo.list_active_by_project(
            project_id,
            item_type=item_type,
            canon_status=canon_status,
            importance=importance,
            keyword=keyword,
            node_kind=node_kind,
        )

    def create_setting(self, project_id: str, data: SettingCreate) -> SettingItem:
        self._ensure_project_exists(project_id)
        node_kind = data.node_kind or "page"

        if node_kind == "folder":
            return self._create_folder(project_id, data)
        else:
            return self._create_page(project_id, data)

    def get_setting(self, setting_id: str) -> SettingItem:
        setting = self.setting_repo.get_active(setting_id)
        if setting is None:
            raise SettingNotFoundError
        return setting

    def update_setting(self, setting_id: str, data: SettingUpdate) -> SettingItem:
        setting = self.get_setting(setting_id)
        values = data.model_dump(exclude_unset=True)

        # System folder protection
        if setting.is_system:
            if "node_kind" in values and values["node_kind"] != "folder":
                raise SettingInvalidNodeKindError("系统目录不能改为设定页")
            values.pop("folder_key", None)
            values.pop("is_system", None)

        # Prevent client from setting folder_key or is_system
        values.pop("folder_key", None)
        values.pop("is_system", None)

        if "parent_id" in values:
            new_parent_id = values["parent_id"]
            if new_parent_id is not None:
                if new_parent_id == setting.id:
                    raise SettingParentCycleError("不能将自己设为父级")
                parent = self.setting_repo.get_active(new_parent_id)
                if parent is None:
                    raise SettingParentNotFoundError
                if parent.project_id != setting.project_id:
                    raise SettingParentProjectMismatchError
                if parent.node_kind != "folder":
                    raise SettingInvalidParentError("父级必须是目录")
                # Cycle detection
                if self._would_create_cycle(setting.project_id, setting.id, new_parent_id):
                    raise SettingParentCycleError("移动会形成循环父子关系")

            # If page moves to new folder without explicit item_type, inherit
            if (
                setting.node_kind == "page"
                and new_parent_id is not None
                and "item_type" not in values
            ):
                new_parent = self.setting_repo.get_active(new_parent_id)
                if new_parent and new_parent.folder_default_item_type:
                    values["item_type"] = new_parent.folder_default_item_type

        return self.setting_repo.update(setting, values)

    def delete_setting(self, setting_id: str) -> SettingItem:
        setting = self.get_setting(setting_id)

        if setting.is_system:
            raise SettingSystemFolderProtectedError("系统目录不能删除")

        if setting.node_kind == "folder":
            children = self.setting_repo.list_active_children(setting.id)
            if children:
                raise SettingFolderNotEmptyError("目录不为空，请先移动或删除子节点")

        return self.setting_repo.soft_delete(setting)

    # --- Private helpers ---

    def _create_folder(self, project_id: str, data: SettingCreate) -> SettingItem:
        parent_id = data.parent_id
        if parent_id is None:
            root = self.setting_repo.get_active_by_project_and_folder_key(project_id, "root")
            if root:
                parent_id = root.id
        else:
            parent = self.setting_repo.get_active(parent_id)
            if parent is None:
                raise SettingParentNotFoundError
            if parent.project_id != project_id:
                raise SettingParentProjectMismatchError
            if parent.node_kind != "folder":
                raise SettingInvalidParentError("目录的父级必须是目录")

        default_type = data.folder_default_item_type or "custom"
        setting = SettingItem(
            id=str(uuid4()),
            project_id=project_id,
            parent_id=parent_id,
            title=data.title,
            item_type=default_type,
            canon_status=data.canon_status,
            summary=data.summary,
            detail=data.detail,
            tags=data.tags,
            order_index=data.order_index,
            importance=data.importance,
            node_kind="folder",
            folder_key=None,
            folder_default_item_type=default_type,
            is_system=False,
        )
        return self.setting_repo.create(setting)

    def _create_page(self, project_id: str, data: SettingCreate) -> SettingItem:
        parent_id = data.parent_id
        if parent_id is None:
            raise SettingInvalidParentError("设定页必须放在目录下")

        parent = self.setting_repo.get_active(parent_id)
        if parent is None:
            raise SettingParentNotFoundError
        if parent.project_id != project_id:
            raise SettingParentProjectMismatchError
        if parent.node_kind != "folder":
            raise SettingInvalidParentError("父级必须是目录")

        item_type = data.item_type
        if not item_type:
            item_type = parent.folder_default_item_type or "custom"

        setting = SettingItem(
            id=str(uuid4()),
            project_id=project_id,
            parent_id=parent_id,
            title=data.title,
            item_type=item_type,
            canon_status=data.canon_status,
            summary=data.summary,
            detail=data.detail,
            tags=data.tags,
            order_index=data.order_index,
            importance=data.importance,
            node_kind="page",
            folder_key=None,
            folder_default_item_type=None,
            is_system=False,
        )
        return self.setting_repo.create(setting)

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise SettingProjectNotFoundError

    def _ensure_default_setting_folders(self, project_id: str) -> None:
        root = self.setting_repo.get_active_by_project_and_folder_key(project_id, "root")
        if root is None:
            root = SettingItem(
                id=str(uuid4()),
                project_id=project_id,
                parent_id=None,
                title=ROOT_FOLDER["title"],
                item_type=ROOT_FOLDER["item_type"],
                canon_status="confirmed",
                summary="",
                detail="",
                tags="",
                order_index=0,
                importance="normal",
                node_kind="folder",
                folder_key=ROOT_FOLDER["folder_key"],
                folder_default_item_type=ROOT_FOLDER["folder_default_item_type"],
                is_system=True,
            )
            self.setting_repo.create(root)

        for folder_def in DEFAULT_FOLDERS:
            existing = self.setting_repo.get_active_by_project_and_folder_key(
                project_id, folder_def["folder_key"]
            )
            if existing is None:
                child = SettingItem(
                    id=str(uuid4()),
                    project_id=project_id,
                    parent_id=root.id,
                    title=folder_def["title"],
                    item_type=folder_def["folder_default_item_type"],
                    canon_status="confirmed",
                    summary="",
                    detail="",
                    tags="",
                    order_index=DEFAULT_FOLDERS.index(folder_def),
                    importance="normal",
                    node_kind="folder",
                    folder_key=folder_def["folder_key"],
                    folder_default_item_type=folder_def["folder_default_item_type"],
                    is_system=True,
                )
                self.setting_repo.create(child)

    def _would_create_cycle(self, project_id: str, node_id: str, new_parent_id: str) -> bool:
        """Check if moving node_id under new_parent_id would create a cycle."""
        current_id = new_parent_id
        visited = set()
        while current_id is not None:
            if current_id in visited:
                return True
            visited.add(current_id)
            if current_id == node_id:
                return True
            ancestor = self.setting_repo.get_active(current_id)
            if ancestor is None:
                break
            current_id = ancestor.parent_id
        return False
