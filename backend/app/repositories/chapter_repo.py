from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chapter import Chapter


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChapterRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project_map(self, project_id: str) -> dict[str, Chapter]:
        return {chapter.id: chapter for chapter in self.list_active_by_project(project_id)}

    def list_active_by_project(self, project_id: str) -> list[Chapter]:
        statement = (
            select(Chapter)
            .where(
                Chapter.project_id == project_id,
                Chapter.deleted_at.is_(None),
            )
            .order_by(
                Chapter.volume_id.asc(),
                Chapter.order_index.asc(),
                Chapter.created_at.asc(),
            )
        )
        return list(self.db.scalars(statement).all())

    def get_active(self, chapter_id: str) -> Chapter | None:
        statement = select(Chapter).where(
            Chapter.id == chapter_id,
            Chapter.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create(self, chapter: Chapter) -> Chapter:
        self.db.add(chapter)
        self.db.commit()
        self.db.refresh(chapter)
        return chapter

    def update(
        self,
        chapter: Chapter,
        values: dict[str, object],
        *,
        commit: bool = True,
    ) -> Chapter:
        for field, value in values.items():
            setattr(chapter, field, value)

        chapter.updated_at = utc_now()
        chapter.version += 1
        if commit:
            self.db.commit()
            self.db.refresh(chapter)
        return chapter

    def soft_delete(self, chapter: Chapter) -> Chapter:
        now = utc_now()
        chapter.deleted_at = now
        chapter.updated_at = now
        chapter.version += 1
        self.db.commit()
        self.db.refresh(chapter)
        return chapter
