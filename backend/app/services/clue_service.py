from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.clue import Clue
from app.repositories.chapter_repo import ChapterRepository
from app.repositories.clue_repo import ClueRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.clue import ClueCreate, ClueUpdate


class ClueNotFoundError(Exception):
    pass


class ClueProjectNotFoundError(Exception):
    pass


class ClueChapterNotFoundError(Exception):
    pass


class ClueChapterProjectMismatchError(Exception):
    pass


class ClueService:
    def __init__(self, db: Session):
        self.clue_repo = ClueRepository(db)
        self.project_repo = ProjectRepository(db)
        self.chapter_repo = ChapterRepository(db)

    def list_project_clues(
        self,
        project_id: str,
        *,
        status: str | None = None,
        visibility: str | None = None,
        importance: str | None = None,
        keyword: str | None = None,
    ) -> list[Clue]:
        if self.project_repo.get_active(project_id) is None:
            raise ClueProjectNotFoundError
        return self.clue_repo.list_active_by_project(
            project_id,
            status=status,
            visibility=visibility,
            importance=importance,
            keyword=keyword,
        )

    def create_clue(self, project_id: str, data: ClueCreate) -> Clue:
        if self.project_repo.get_active(project_id) is None:
            raise ClueProjectNotFoundError

        self._validate_chapter(project_id, data.setup_chapter_id)
        self._validate_chapter(project_id, data.payoff_chapter_id)

        clue = Clue(id=str(uuid4()), project_id=project_id, **data.model_dump())
        return self.clue_repo.create(clue)

    def get_clue(self, clue_id: str) -> Clue:
        clue = self.clue_repo.get_active(clue_id)
        if clue is None:
            raise ClueNotFoundError
        return clue

    def update_clue(self, clue_id: str, data: ClueUpdate) -> Clue:
        clue = self.get_clue(clue_id)
        values = data.model_dump(exclude_unset=True)
        if "setup_chapter_id" in values:
            self._validate_chapter(clue.project_id, values["setup_chapter_id"])
        if "payoff_chapter_id" in values:
            self._validate_chapter(clue.project_id, values["payoff_chapter_id"])
        return self.clue_repo.update(clue, values)

    def delete_clue(self, clue_id: str) -> Clue:
        clue = self.get_clue(clue_id)
        return self.clue_repo.soft_delete(clue)

    def _validate_chapter(self, project_id: str, chapter_id: object) -> None:
        if chapter_id is None:
            return
        chapter = self.chapter_repo.get_active(str(chapter_id))
        if chapter is None:
            raise ClueChapterNotFoundError
        if chapter.project_id != project_id:
            raise ClueChapterProjectMismatchError
