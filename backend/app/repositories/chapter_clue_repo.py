from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chapter_clue import ChapterClue
from app.models.clue import Clue


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChapterClueRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_chapter(self, chapter_id: str) -> list[tuple[ChapterClue, Clue]]:
        statement = (
            select(ChapterClue, Clue)
            .join(Clue, ChapterClue.clue_id == Clue.id)
            .where(
                ChapterClue.chapter_id == chapter_id,
                ChapterClue.deleted_at.is_(None),
                Clue.deleted_at.is_(None),
            )
            .order_by(ChapterClue.created_at.asc())
        )
        return list(self.db.execute(statement).all())

    def get(self, link_id: str) -> ChapterClue | None:
        return self.db.scalar(select(ChapterClue).where(ChapterClue.id == link_id))

    def create(self, link: ChapterClue) -> ChapterClue:
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def update(self, link: ChapterClue, values: dict[str, object]) -> ChapterClue:
        for field, value in values.items():
            setattr(link, field, value)
        link.updated_at = utc_now()
        link.version = (link.version or 0) + 1
        self.db.commit()
        self.db.refresh(link)
        return link

    def delete(self, link: ChapterClue) -> ChapterClue:
        link.deleted_at = utc_now()
        link.updated_at = utc_now()
        link.version = (link.version or 0) + 1
        self.db.commit()
        self.db.refresh(link)
        return link
