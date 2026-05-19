from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.chapter_version import ChapterVersion
from app.repositories.chapter_repo import ChapterRepository
from app.repositories.chapter_version_repo import ChapterVersionRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.volume_repo import VolumeRepository
from app.schemas.chapter import ChapterCreate, ChapterUpdate


AUTOSAVE_VERSION_INTERVAL_SECONDS = 5 * 60
AUTOSAVE_CONTENT_DELTA_THRESHOLD = 200


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
        self.db = db
        self.chapter_repo = ChapterRepository(db)
        self.version_repo = ChapterVersionRepository(db)
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
        save_source = values.pop("save_source", "manual")
        original_content = chapter.content
        content_changed = "content" in values and values["content"] != original_content

        if "volume_id" in values:
            self._ensure_volume_belongs_to_project(
                project_id=chapter.project_id,
                volume_id=values["volume_id"],
            )

        if "content" in values:
            if values["content"] is None:
                values["content"] = ""
            values["word_count"] = calculate_word_count(str(values["content"]))

        try:
            updated_chapter = self.chapter_repo.update(chapter, values, commit=False)
            if content_changed:
                self._create_content_version_if_needed(updated_chapter, str(save_source))

            self.db.commit()
            self.db.refresh(updated_chapter)
            return updated_chapter
        except Exception:
            self.db.rollback()
            raise

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

    def _create_content_version_if_needed(self, chapter: Chapter, source: str) -> None:
        latest = self.version_repo.get_latest_by_chapter(chapter.id)
        if latest is not None and latest.content == chapter.content:
            return

        if source == "autosave" and not self._should_create_autosave_version(chapter, latest):
            return

        version = ChapterVersion(
            id=str(uuid4()),
            chapter_id=chapter.id,
            project_id=chapter.project_id,
            title=chapter.title,
            content=chapter.content,
            word_count=chapter.word_count,
            source=source,
            note="手动保存" if source == "manual" else "自动保存",
        )
        self.version_repo.create(version, commit=False)

    def _should_create_autosave_version(
        self,
        chapter: Chapter,
        latest: ChapterVersion | None,
    ) -> bool:
        if latest is None:
            return True

        latest_created_at = latest.created_at
        if latest_created_at.tzinfo is None:
            latest_created_at = latest_created_at.replace(tzinfo=timezone.utc)

        age_seconds = (datetime.now(timezone.utc) - latest_created_at).total_seconds()
        content_delta = abs(
            calculate_word_count(chapter.content) - calculate_word_count(latest.content)
        )
        return (
            age_seconds >= AUTOSAVE_VERSION_INTERVAL_SECONDS
            or content_delta >= AUTOSAVE_CONTENT_DELTA_THRESHOLD
        )
