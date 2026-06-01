from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.character import Character


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CharacterRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active_by_project(
        self,
        project_id: str,
        *,
        role: str | None = None,
        importance: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> list[Character]:
        statement = select(Character).where(
            Character.project_id == project_id,
            Character.deleted_at.is_(None),
        )

        if role is not None:
            statement = statement.where(Character.role == role)
        if importance is not None:
            statement = statement.where(Character.importance == importance)
        if status is not None:
            statement = statement.where(Character.status == status)
        if keyword:
            pattern = f"%{keyword}%"
            statement = statement.where(
                or_(
                    Character.name.ilike(pattern),
                    Character.summary.ilike(pattern),
                    Character.biography.ilike(pattern),
                    Character.faction.ilike(pattern),
                    Character.profile_sections.ilike(pattern),
                )
            )

        statement = statement.order_by(
            Character.importance.desc(),
            Character.updated_at.desc(),
            Character.created_at.desc(),
        )
        return list(self.db.scalars(statement).all())

    def get_active(self, character_id: str) -> Character | None:
        statement = select(Character).where(
            Character.id == character_id,
            Character.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create(self, character: Character) -> Character:
        self.db.add(character)
        self.db.commit()
        self.db.refresh(character)
        return character

    def update(self, character: Character, values: dict[str, object]) -> Character:
        for field, value in values.items():
            setattr(character, field, value)

        character.updated_at = utc_now()
        character.version += 1
        self.db.commit()
        self.db.refresh(character)
        return character

    def soft_delete(self, character: Character) -> Character:
        now = utc_now()
        character.deleted_at = now
        character.updated_at = now
        character.version += 1
        self.db.commit()
        self.db.refresh(character)
        return character
