from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.clue_character import ClueCharacter
from app.repositories.character_repo import CharacterRepository
from app.repositories.clue_character_repo import ClueCharacterRepository
from app.repositories.clue_repo import ClueRepository
from app.schemas.clue import ClueCharacterCreate, ClueCharacterUpdate


class ClueCharacterLinkNotFoundError(Exception):
    pass


class ClueCharacterClueNotFoundError(Exception):
    pass


class ClueCharacterCharacterNotFoundError(Exception):
    pass


class ClueCharacterProjectMismatchError(Exception):
    pass


class ClueCharacterService:
    def __init__(self, db: Session):
        self.link_repo = ClueCharacterRepository(db)
        self.clue_repo = ClueRepository(db)
        self.character_repo = CharacterRepository(db)

    def list_clue_characters(self, clue_id: str) -> list[dict[str, object]]:
        clue = self.clue_repo.get_active(clue_id)
        if clue is None:
            raise ClueCharacterClueNotFoundError
        return [self._to_read_payload(link, character) for link, character in self.link_repo.list_active_by_clue(clue_id)]

    def add_clue_character(self, clue_id: str, data: ClueCharacterCreate) -> dict[str, object]:
        clue = self.clue_repo.get_active(clue_id)
        if clue is None:
            raise ClueCharacterClueNotFoundError
        character = self.character_repo.get_active(data.character_id)
        if character is None:
            raise ClueCharacterCharacterNotFoundError
        if character.project_id != clue.project_id:
            raise ClueCharacterProjectMismatchError
        link = ClueCharacter(
            id=str(uuid4()),
            project_id=clue.project_id,
            clue_id=clue.id,
            character_id=character.id,
            relation_type=data.relation_type,
            note=data.note,
        )
        return self._to_read_payload(self.link_repo.create(link), character)

    def update_clue_character(self, link_id: str, data: ClueCharacterUpdate) -> dict[str, object]:
        link = self.link_repo.get(link_id)
        if link is None:
            raise ClueCharacterLinkNotFoundError
        updated = self.link_repo.update(link, data.model_dump(exclude_unset=True))
        character = self.character_repo.get_active(updated.character_id)
        if character is None:
            raise ClueCharacterCharacterNotFoundError
        return self._to_read_payload(updated, character)

    def delete_clue_character(self, link_id: str) -> None:
        link = self.link_repo.get(link_id)
        if link is None:
            raise ClueCharacterLinkNotFoundError
        self.link_repo.delete(link)

    def _to_read_payload(self, link: ClueCharacter, character) -> dict[str, object]:
        return {
            "id": link.id,
            "project_id": link.project_id,
            "clue_id": link.clue_id,
            "character_id": link.character_id,
            "relation_type": link.relation_type,
            "note": link.note,
            "created_at": link.created_at,
            "updated_at": link.updated_at,
            "character": character,
        }
