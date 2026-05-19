from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.repositories.chapter_repo import ChapterRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.volume_repo import VolumeRepository
from app.schemas.chapter import ChapterCreate, ChapterUpdate


class ChapterNotFoundError(Exception):
    pass


class ChapterProjectNotFoundError(Exception):
    pass


class ChapterVolumeNotFoundError(Exception):
    pass


def calculate_word_count(content: str) -> int:
    return sum(1 for character in content if not character.isspace())


class ChapterService:
    def __init__(self, db: Session):
        self.chapter_repo = ChapterRepository(db)
        self.project_repo = ProjectRepository(db)
        self.volume_repo = VolumeRepository(db)

    def list_project_chapters(self, project_id: str) -> list[Chapter]:
        self._ensure_project_exists(project_id)
        return self.chapter_repo.list_active_by_project(project_id)

    def create_chapter(self, project_id: str, data: ChapterCreate) -> Chapter:
        self._ensure_project_exists(project_id)
        self._ensure_volume_belongs_to_project(project_id, data.volume_id)

        chapter = Chapter(
            id=str(uuid4()),
            project_id=project_id,
            volume_id=data.volume_id,
            title=data.title,
            content=data.content,
            order_index=data.order_index,
            status=data.status,
            word_count=calculate_word_count(data.content),
        )
        return self.chapter_repo.create(chapter)

    def get_chapter(self, chapter_id: str) -> Chapter:
        chapter = self.chapter_repo.get_active(chapter_id)
        if chapter is None:
            raise ChapterNotFoundError
        return chapter

    def update_chapter(self, chapter_id: str, data: ChapterUpdate) -> Chapter:
        chapter = self.get_chapter(chapter_id)
        values = data.model_dump(exclude_unset=True)

        if "volume_id" in values:
            self._ensure_volume_belongs_to_project(
                project_id=chapter.project_id,
                volume_id=values["volume_id"],
            )

        if "content" in values:
            if values["content"] is None:
                values["content"] = ""
            values["word_count"] = calculate_word_count(str(values["content"]))

        return self.chapter_repo.update(chapter, values)

    def delete_chapter(self, chapter_id: str) -> Chapter:
        chapter = self.get_chapter(chapter_id)
        return self.chapter_repo.soft_delete(chapter)

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise ChapterProjectNotFoundError

    def _ensure_volume_belongs_to_project(
        self,
        project_id: str,
        volume_id: object,
    ) -> None:
        if volume_id is None:
            return

        volume = self.volume_repo.get_active(str(volume_id))
        if volume is None or volume.project_id != project_id:
            raise ChapterVolumeNotFoundError
