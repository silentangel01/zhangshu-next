from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.project_repo import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate, encode_tags


class ProjectNotFoundError(Exception):
    pass


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProjectRepository(db)

    def list_projects(self) -> list[Project]:
        return self.repo.list_active()

    def create_project(self, data: ProjectCreate) -> Project:
        project = Project(
            id=str(uuid4()),
            title=data.title,
            author=data.author,
            genre=data.genre,
            summary=data.summary,
            tags=encode_tags(data.tags),
            status=data.status,
            target_word_count=data.target_word_count,
        )
        created = self.repo.create(project)
        self._mark_dirty(created.id, "upsert")
        return created

    def get_project(self, project_id: str) -> Project:
        project = self.repo.get_active(project_id)
        if project is None:
            raise ProjectNotFoundError
        return project

    def update_project(self, project_id: str, data: ProjectUpdate) -> Project:
        project = self.get_project(project_id)
        values = data.model_dump(exclude_unset=True)
        if "tags" in values:
            values["tags"] = encode_tags(values["tags"])
        updated = self.repo.update(project, values)
        self._mark_dirty(project_id, "upsert")
        return updated

    def update_project_raw(
        self, project_id: str, values: dict[str, object]
    ) -> Project:
        project = self.get_project(project_id)
        updated = self.repo.update(project, values)
        self._mark_dirty(project_id, "upsert")
        return updated

    def delete_project(self, project_id: str) -> Project:
        project = self.get_project(project_id)
        deleted = self.repo.soft_delete(project)
        self._mark_dirty(project_id, "delete")
        return deleted

    def _mark_dirty(self, project_id: str, action: str) -> None:
        """Mark the project as dirty for cloud sync (best-effort, never raises)."""
        try:
            from app.services.sync_dirty_service import SyncDirtyService

            SyncDirtyService(self.db).mark_dirty(project_id, "projects", project_id, action)
        except Exception:
            pass
