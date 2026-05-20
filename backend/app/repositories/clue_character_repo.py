from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.character import Character
from app.models.clue_character import ClueCharacter


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ClueCharacterRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_clue(self, clue_id: str) -> list[tuple[ClueCharacter, Character]]:
        statement = (
            select(ClueCharacter, Character)
            .join(Character, ClueCharacter.character_id == Character.id)
            .where(ClueCharacter.clue_id == clue_id, Character.deleted_at.is_(None))
            .order_by(ClueCharacter.created_at.asc())
        )
        return list(self.db.execute(statement).all())

    def get(self, link_id: str) -> ClueCharacter | None:
        return self.db.scalar(select(ClueCharacter).where(ClueCharacter.id == link_id))

    def create(self, link: ClueCharacter) -> ClueCharacter:
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def update(self, link: ClueCharacter, values: dict[str, object]) -> ClueCharacter:
        for field, value in values.items():
            setattr(link, field, value)
        link.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(link)
        return link

    def delete(self, link: ClueCharacter) -> None:
        self.db.delete(link)
        self.db.commit()
