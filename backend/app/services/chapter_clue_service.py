from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.chapter_clue import ChapterClue
from app.repositories.chapter_clue_repo import ChapterClueRepository
from app.repositories.chapter_repo import ChapterRepository
from app.repositories.clue_repo import ClueRepository
from app.schemas.clue import ChapterClueCreate, ChapterClueUpdate


class ChapterClueLinkNotFoundError(Exception):
    pass


class ChapterClueChapterNotFoundError(Exception):
    pass


class ChapterClueClueNotFoundError(Exception):
    pass


class ChapterClueProjectMismatchError(Exception):
    pass


class ChapterClueService:
    def __init__(self, db: Session):
        self.link_repo = ChapterClueRepository(db)
        self.chapter_repo = ChapterRepository(db)
        self.clue_repo = ClueRepository(db)

    def list_chapter_clues(self, chapter_id: str) -> list[dict[str, object]]:
        chapter = self.chapter_repo.get_active(chapter_id)
        if chapter is None:
            raise ChapterClueChapterNotFoundError
        return [self._to_read_payload(link, clue) for link, clue in self.link_repo.list_active_by_chapter(chapter_id)]

    def add_chapter_clue(self, chapter_id: str, data: ChapterClueCreate) -> dict[str, object]:
        chapter = self.chapter_repo.get_active(chapter_id)
        if chapter is None:
            raise ChapterClueChapterNotFoundError
        clue = self.clue_repo.get_active(data.clue_id)
        if clue is None:
            raise ChapterClueClueNotFoundError
        if clue.project_id != chapter.project_id:
            raise ChapterClueProjectMismatchError

        link = ChapterClue(
            id=str(uuid4()),
            project_id=chapter.project_id,
            chapter_id=chapter.id,
            clue_id=clue.id,
            relation_type=data.relation_type,
            note=data.note,
        )
        created = self.link_repo.create(link)
        self._apply_convenience_updates(clue, chapter.id, data.relation_type)
        clue = self.clue_repo.get_active(clue.id) or clue
        return self._to_read_payload(created, clue)

    def update_chapter_clue(self, link_id: str, data: ChapterClueUpdate) -> dict[str, object]:
        link = self.link_repo.get(link_id)
        if link is None:
            raise ChapterClueLinkNotFoundError
        values = data.model_dump(exclude_unset=True)
        updated = self.link_repo.update(link, values)
        clue = self.clue_repo.get_active(updated.clue_id)
        if clue is None:
            raise ChapterClueClueNotFoundError
        if "relation_type" in values:
            self._apply_convenience_updates(clue, updated.chapter_id, str(values["relation_type"]))
            clue = self.clue_repo.get_active(updated.clue_id) or clue
        return self._to_read_payload(updated, clue)

    def delete_chapter_clue(self, link_id: str) -> None:
        link = self.link_repo.get(link_id)
        if link is None:
            raise ChapterClueLinkNotFoundError
        self.link_repo.delete(link)

    def _apply_convenience_updates(self, clue, chapter_id: str, relation_type: str) -> None:
        values: dict[str, object] = {}
        if relation_type == "setup":
            if clue.setup_chapter_id is None:
                values["setup_chapter_id"] = chapter_id
            if clue.status == "planned":
                values["status"] = "planted"
        if relation_type == "payoff":
            if clue.payoff_chapter_id is None:
                values["payoff_chapter_id"] = chapter_id
            if clue.status != "abandoned":
                values["status"] = "resolved"
        if values:
            self.clue_repo.update(clue, values)

    def _to_read_payload(self, link: ChapterClue, clue) -> dict[str, object]:
        return {
            "id": link.id,
            "project_id": link.project_id,
            "chapter_id": link.chapter_id,
            "clue_id": link.clue_id,
            "relation_type": link.relation_type,
            "note": link.note,
            "created_at": link.created_at,
            "updated_at": link.updated_at,
            "clue": clue,
        }
