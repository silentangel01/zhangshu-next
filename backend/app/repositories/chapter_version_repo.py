from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chapter_version import ChapterVersion


class ChapterVersionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_chapter(self, chapter_id: str) -> list[ChapterVersion]:
        statement = (
            select(ChapterVersion)
            .where(ChapterVersion.chapter_id == chapter_id)
            .order_by(ChapterVersion.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get(self, version_id: str) -> ChapterVersion | None:
        statement = select(ChapterVersion).where(ChapterVersion.id == version_id)
        return self.db.scalar(statement)

    def get_latest_by_chapter(self, chapter_id: str) -> ChapterVersion | None:
        statement = (
            select(ChapterVersion)
            .where(ChapterVersion.chapter_id == chapter_id)
            .order_by(ChapterVersion.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def create(self, version: ChapterVersion, *, commit: bool = True) -> ChapterVersion:
        self.db.add(version)
        if commit:
            self.db.commit()
            self.db.refresh(version)
        return version
