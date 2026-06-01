from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.character import Character
from app.repositories.character_repo import CharacterRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.character import (
    CharacterCreate,
    CharacterUpdate,
    encode_profile_dimensions,
    encode_profile_sections,
)


class CharacterNotFoundError(Exception):
    pass


class CharacterProjectNotFoundError(Exception):
    pass


class CharacterService:
    def __init__(self, db: Session):
        self.db = db
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
            profile_sections=encode_profile_sections(data.profile_sections),
            profile_dimensions=encode_profile_dimensions(data.profile_dimensions),
        )
        created = self.character_repo.create(character)
        self._mark_dirty(project_id, created.id, "upsert")
        return created

    def get_character(self, character_id: str) -> Character:
        character = self.character_repo.get_active(character_id)
        if character is None:
            raise CharacterNotFoundError
        return character

    def update_character(self, character_id: str, data: CharacterUpdate) -> Character:
        character = self.get_character(character_id)
        values = data.model_dump(exclude_unset=True)
        # Encode array fields to JSON strings for DB storage
        if "profile_sections" in values:
            values["profile_sections"] = encode_profile_sections(values["profile_sections"])
        if "profile_dimensions" in values:
            values["profile_dimensions"] = encode_profile_dimensions(values["profile_dimensions"])
        updated = self.character_repo.update(character, values)
        self._mark_dirty(character.project_id, character_id, "upsert")
        return updated

    def delete_character(self, character_id: str) -> Character:
        character = self.get_character(character_id)
        deleted = self.character_repo.soft_delete(character)
        self._mark_dirty(character.project_id, character_id, "delete")
        return deleted

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise CharacterProjectNotFoundError

    def _mark_dirty(self, project_id: str, entity_id: str, action: str) -> None:
        """Mark the character as dirty for cloud sync (best-effort, never raises)."""
        try:
            from app.services.sync_dirty_service import SyncDirtyService

            SyncDirtyService(self.db).mark_dirty(project_id, "characters", entity_id, action)
        except Exception:
            pass
