from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.chapter_version import ChapterVersion
from app.repositories.chapter_repo import ChapterRepository
from app.repositories.chapter_version_repo import ChapterVersionRepository
from app.schemas.chapter_version import ChapterVersionSource, CreateChapterVersionRequest
from app.services.chapter_service import ChapterNotFoundError, calculate_word_count


AUTOSAVE_VERSION_INTERVAL_SECONDS = 5 * 60
AUTOSAVE_CONTENT_DELTA_THRESHOLD = 200


class ChapterVersionNotFoundError(Exception):
    pass


class ChapterVersionMismatchError(Exception):
    pass


class ChapterVersionService:
    def __init__(self, db: Session):
        self.db = db
        self.chapter_repo = ChapterRepository(db)
        self.version_repo = ChapterVersionRepository(db)

    def list_versions(self, chapter_id: str) -> list[ChapterVersion]:
        self._get_active_chapter(chapter_id)
        return self.version_repo.list_by_chapter(chapter_id)

    def get_version(self, version_id: str) -> ChapterVersion:
        version = self.version_repo.get(version_id)
        if version is None:
            raise ChapterVersionNotFoundError
        return version

    def create_snapshot(
        self,
        chapter_id: str,
        data: CreateChapterVersionRequest,
    ) -> ChapterVersion:
        chapter = self._get_active_chapter(chapter_id)
        version = self.create_snapshot_for_chapter(
            chapter,
            source=data.source,
            note=data.note,
            force=data.source in {"restore", "before_restore"},
            commit=True,
        )
        if version is None:
            latest = self.version_repo.get_latest_by_chapter(chapter.id)
            if latest is None:
                raise ChapterVersionNotFoundError
            return latest
        return version

    def create_snapshot_for_chapter(
        self,
        chapter: Chapter,
        *,
        source: ChapterVersionSource,
        note: str | None = None,
        force: bool = False,
        commit: bool = False,
    ) -> ChapterVersion | None:
        latest = self.version_repo.get_latest_by_chapter(chapter.id)
        if not force and latest is not None and latest.content == chapter.content:
            return None

        if not force and source == "autosave" and not self._should_create_autosave_version(chapter, latest):
            return None

        version = ChapterVersion(
            id=str(uuid4()),
            chapter_id=chapter.id,
            project_id=chapter.project_id,
            title=chapter.title,
            content=chapter.content,
            word_count=chapter.word_count,
            source=source,
            note=note,
        )
        return self.version_repo.create(version, commit=commit)

    def restore_version(self, chapter_id: str, version_id: str) -> Chapter:
        chapter = self._get_active_chapter(chapter_id)
        version = self.get_version(version_id)
        if version.chapter_id != chapter.id:
            raise ChapterVersionMismatchError

        try:
            self.create_snapshot_for_chapter(
                chapter,
                source="before_restore",
                note="恢复版本前自动备份",
                force=True,
                commit=False,
            )
            updated_chapter = self.chapter_repo.update(
                chapter,
                {
                    "title": version.title,
                    "content": version.content,
                    "word_count": calculate_word_count(version.content),
                },
                commit=False,
            )
            self.db.flush()
            self.create_snapshot_for_chapter(
                updated_chapter,
                source="restore",
                note=f"从版本 {version.id} 恢复",
                force=True,
                commit=False,
            )
            self.db.commit()
            self.db.refresh(updated_chapter)
            return updated_chapter
        except Exception:
            self.db.rollback()
            raise

    def _get_active_chapter(self, chapter_id: str) -> Chapter:
        chapter = self.chapter_repo.get_active(chapter_id)
        if chapter is None:
            raise ChapterNotFoundError
        return chapter

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
