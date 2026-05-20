from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.chapter_character import ChapterCharacter
from app.repositories.chapter_character_repo import ChapterCharacterRepository
from app.repositories.chapter_repo import ChapterRepository
from app.repositories.character_repo import CharacterRepository
from app.schemas.character import ChapterCharacterCreate, ChapterCharacterUpdate


class ChapterCharacterLinkNotFoundError(Exception):
    pass


class ChapterCharacterChapterNotFoundError(Exception):
    pass


class ChapterCharacterCharacterNotFoundError(Exception):
    pass


class ChapterCharacterProjectMismatchError(Exception):
    pass


class ChapterCharacterService:
    def __init__(self, db: Session):
        self.link_repo = ChapterCharacterRepository(db)
        self.chapter_repo = ChapterRepository(db)
        self.character_repo = CharacterRepository(db)

    def list_chapter_characters(self, chapter_id: str) -> list[dict[str, object]]:
        chapter = self.chapter_repo.get_active(chapter_id)
        if chapter is None:
            raise ChapterCharacterChapterNotFoundError

        return [
            self._to_read_payload(link, character)
            for link, character in self.link_repo.list_active_by_chapter(chapter_id)
        ]

    def add_chapter_character(
        self,
        chapter_id: str,
        data: ChapterCharacterCreate,
    ) -> dict[str, object]:
        chapter = self.chapter_repo.get_active(chapter_id)
        if chapter is None:
            raise ChapterCharacterChapterNotFoundError

        character = self.character_repo.get_active(data.character_id)
        if character is None:
            raise ChapterCharacterCharacterNotFoundError
        if character.project_id != chapter.project_id:
            raise ChapterCharacterProjectMismatchError

        link = ChapterCharacter(
            id=str(uuid4()),
            project_id=chapter.project_id,
            chapter_id=chapter.id,
            character_id=character.id,
            relation_type=data.relation_type,
            note=data.note,
        )
        created = self.link_repo.create(link)
        return self._to_read_payload(created, character)

    def update_chapter_character(
        self,
        link_id: str,
        data: ChapterCharacterUpdate,
    ) -> dict[str, object]:
        link = self.link_repo.get(link_id)
        if link is None:
            raise ChapterCharacterLinkNotFoundError

        values = data.model_dump(exclude_unset=True)
        updated = self.link_repo.update(link, values)
        character = self.character_repo.get_active(updated.character_id)
        if character is None:
            raise ChapterCharacterCharacterNotFoundError
        return self._to_read_payload(updated, character)

    def delete_chapter_character(self, link_id: str) -> None:
        link = self.link_repo.get(link_id)
        if link is None:
            raise ChapterCharacterLinkNotFoundError
        self.link_repo.delete(link)

    def _to_read_payload(
        self,
        link: ChapterCharacter,
        character,
    ) -> dict[str, object]:
        return {
            "id": link.id,
            "project_id": link.project_id,
            "chapter_id": link.chapter_id,
            "character_id": link.character_id,
            "relation_type": link.relation_type,
            "note": link.note,
            "created_at": link.created_at,
            "updated_at": link.updated_at,
            "character": character,
        }
