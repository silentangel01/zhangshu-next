from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.chapter_setting import ChapterSetting
from app.repositories.chapter_repo import ChapterRepository
from app.repositories.chapter_setting_repo import ChapterSettingRepository
from app.repositories.setting_repo import SettingRepository
from app.schemas.setting import ChapterSettingCreate, ChapterSettingUpdate


class ChapterSettingLinkNotFoundError(Exception):
    pass


class ChapterSettingChapterNotFoundError(Exception):
    pass


class ChapterSettingItemNotFoundError(Exception):
    pass


class ChapterSettingProjectMismatchError(Exception):
    pass


class ChapterSettingService:
    def __init__(self, db: Session):
        self.link_repo = ChapterSettingRepository(db)
        self.chapter_repo = ChapterRepository(db)
        self.setting_repo = SettingRepository(db)

    def list_chapter_settings(self, chapter_id: str) -> list[dict[str, object]]:
        chapter = self.chapter_repo.get_active(chapter_id)
        if chapter is None:
            raise ChapterSettingChapterNotFoundError

        return [
            self._to_read_payload(link, setting_item)
            for link, setting_item in self.link_repo.list_active_by_chapter(chapter_id)
        ]

    def add_chapter_setting(
        self,
        chapter_id: str,
        data: ChapterSettingCreate,
    ) -> dict[str, object]:
        chapter = self.chapter_repo.get_active(chapter_id)
        if chapter is None:
            raise ChapterSettingChapterNotFoundError

        setting_item = self.setting_repo.get_active(data.setting_item_id)
        if setting_item is None:
            raise ChapterSettingItemNotFoundError
        if setting_item.project_id != chapter.project_id:
            raise ChapterSettingProjectMismatchError

        link = ChapterSetting(
            id=str(uuid4()),
            project_id=chapter.project_id,
            chapter_id=chapter.id,
            setting_item_id=setting_item.id,
            relation_type=data.relation_type,
            note=data.note,
        )
        created = self.link_repo.create(link)
        return self._to_read_payload(created, setting_item)

    def update_chapter_setting(
        self,
        link_id: str,
        data: ChapterSettingUpdate,
    ) -> dict[str, object]:
        link = self.link_repo.get(link_id)
        if link is None:
            raise ChapterSettingLinkNotFoundError

        values = data.model_dump(exclude_unset=True)
        updated = self.link_repo.update(link, values)
        setting_item = self.setting_repo.get_active(updated.setting_item_id)
        if setting_item is None:
            raise ChapterSettingItemNotFoundError
        return self._to_read_payload(updated, setting_item)

    def delete_chapter_setting(self, link_id: str) -> None:
        link = self.link_repo.get(link_id)
        if link is None:
            raise ChapterSettingLinkNotFoundError
        self.link_repo.delete(link)

    def _to_read_payload(
        self,
        link: ChapterSetting,
        setting_item,
    ) -> dict[str, object]:
        return {
            "id": link.id,
            "project_id": link.project_id,
            "chapter_id": link.chapter_id,
            "setting_item_id": link.setting_item_id,
            "relation_type": link.relation_type,
            "note": link.note,
            "created_at": link.created_at,
            "updated_at": link.updated_at,
            "setting_item": setting_item,
        }
