from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.chapter_version import ChapterVersion


class ChapterVersionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_chapter(self, chapter_id: str) -> list[ChapterVersion]:
        statement = (
            select(ChapterVersion)
            .where(
                ChapterVersion.chapter_id == chapter_id,
                ChapterVersion.deleted_at.is_(None),
            )
            .order_by(ChapterVersion.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get(self, version_id: str) -> ChapterVersion | None:
        return self.db.scalar(
            select(ChapterVersion).where(
                ChapterVersion.id == version_id,
                ChapterVersion.deleted_at.is_(None),
            )
        )

    def get_latest_by_chapter(self, chapter_id: str) -> ChapterVersion | None:
        statement = (
            select(ChapterVersion)
            .where(
                ChapterVersion.chapter_id == chapter_id,
                ChapterVersion.deleted_at.is_(None),
            )
            .order_by(ChapterVersion.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def list_by_project(
        self,
        project_id: str,
        *,
        entity_id: str | None = None,
        source: str | None = None,
        pinned: bool | None = None,
        keyword: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ChapterVersion], int]:
        base = select(ChapterVersion).where(
            ChapterVersion.project_id == project_id,
            ChapterVersion.deleted_at.is_(None),
        )
        if entity_id:
            base = base.where(ChapterVersion.chapter_id == entity_id)
        if source:
            base = base.where(ChapterVersion.source == source)
        if pinned is not None:
            base = base.where(ChapterVersion.is_pinned == pinned)
        if keyword:
            pattern = f"%{keyword}%"
            base = base.where(
                ChapterVersion.title.like(pattern)
                | ChapterVersion.label.like(pattern)
                | ChapterVersion.note.like(pattern)
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = base.order_by(ChapterVersion.created_at.desc()).limit(limit).offset(offset)
        rows = list(self.db.scalars(stmt).all())
        return rows, total

    def create(self, version: ChapterVersion, *, commit: bool = True) -> ChapterVersion:
        self.db.add(version)
        if commit:
            self.db.commit()
            self.db.refresh(version)
        return version

    def update(
        self,
        version: ChapterVersion,
        values: dict,
        *,
        commit: bool = True,
    ) -> ChapterVersion:
        for key, value in values.items():
            setattr(version, key, value)
        if commit:
            self.db.commit()
            self.db.refresh(version)
        return version

    def soft_delete(self, version: ChapterVersion, *, commit: bool = True) -> None:
        version.deleted_at = datetime.now(timezone.utc)
        if commit:
            self.db.commit()

    def cleanup_unpinned_autosave(
        self,
        project_id: str,
        *,
        keep_days: int = 30,
        commit: bool = True,
    ) -> int:
        """Soft-delete old autosave versions that are not pinned."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
        old_versions = list(
            self.db.scalars(
                select(ChapterVersion).where(
                    ChapterVersion.project_id == project_id,
                    ChapterVersion.source == "autosave",
                    ChapterVersion.is_pinned == False,  # noqa: E712
                    ChapterVersion.deleted_at.is_(None),
                    ChapterVersion.created_at < cutoff,
                )
            ).all()
        )
        now = datetime.now(timezone.utc)
        for v in old_versions:
            v.deleted_at = now
        if commit:
            self.db.commit()
        return len(old_versions)
