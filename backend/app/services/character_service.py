from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.character import Character
from app.repositories.character_repo import CharacterRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.character import CharacterCreate, CharacterUpdate


class CharacterNotFoundError(Exception):
    pass


class CharacterProjectNotFoundError(Exception):
    pass


class CharacterService:
    def __init__(self, db: Session):
        self.character_repo = CharacterRepository(db)
        self.project_repo = ProjectRepository(db)

    def list_project_characters(
        self,
        project_id: str,
        *,
        role: str | None = None,
        importance: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> list[Character]:
        self._ensure_project_exists(project_id)
        return self.character_repo.list_active_by_project(
            project_id,
            role=role,
            importance=importance,
            status=status,
            keyword=keyword,
        )

    def create_character(self, project_id: str, data: CharacterCreate) -> Character:
        self._ensure_project_exists(project_id)
        character = Character(
            id=str(uuid4()),
            project_id=project_id,
            name=data.name,
            role=data.role,
            importance=data.importance,
            status=data.status,
            faction=data.faction,
            summary=data.summary,
            biography=data.biography,
            appearance=data.appearance,
            personality=data.personality,
            background=data.background,
            ability=data.ability,
            motivation=data.motivation,
            secret=data.secret,
            arc=data.arc,
            notes=data.notes,
        )
        return self.character_repo.create(character)

    def get_character(self, character_id: str) -> Character:
        character = self.character_repo.get_active(character_id)
        if character is None:
            raise CharacterNotFoundError
        return character

    def update_character(self, character_id: str, data: CharacterUpdate) -> Character:
        character = self.get_character(character_id)
        values = data.model_dump(exclude_unset=True)
        return self.character_repo.update(character, values)

    def delete_character(self, character_id: str) -> Character:
        character = self.get_character(character_id)
        return self.character_repo.soft_delete(character)

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise CharacterProjectNotFoundError
