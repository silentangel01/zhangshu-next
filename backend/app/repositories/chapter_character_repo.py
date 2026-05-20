from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.character import Character
from app.models.chapter_character import ChapterCharacter


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChapterCharacterRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_chapter(self, chapter_id: str) -> list[tuple[ChapterCharacter, Character]]:
        statement = (
            select(ChapterCharacter, Character)
            .join(Character, ChapterCharacter.character_id == Character.id)
            .where(
                ChapterCharacter.chapter_id == chapter_id,
                Character.deleted_at.is_(None),
            )
            .order_by(ChapterCharacter.created_at.asc())
        )
        return list(self.db.execute(statement).all())

    def get(self, link_id: str) -> ChapterCharacter | None:
        statement = select(ChapterCharacter).where(ChapterCharacter.id == link_id)
        return self.db.scalar(statement)

    def create(self, link: ChapterCharacter) -> ChapterCharacter:
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def update(self, link: ChapterCharacter, values: dict[str, object]) -> ChapterCharacter:
        for field, value in values.items():
            setattr(link, field, value)

        link.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(link)
        return link

    def delete(self, link: ChapterCharacter) -> None:
        self.db.delete(link)
        self.db.commit()
