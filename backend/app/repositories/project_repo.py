from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active(self) -> list[Project]:
        statement = (
            select(Project)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.updated_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_active(self, project_id: str) -> Project | None:
        statement = select(Project).where(
            Project.id == project_id,
            Project.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def create(self, project: Project) -> Project:
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def update(self, project: Project, values: dict[str, object]) -> Project:
        for field, value in values.items():
            setattr(project, field, value)

        project.updated_at = utc_now()
        project.version += 1
        self.db.commit()
        self.db.refresh(project)
        return project

    def soft_delete(self, project: Project) -> Project:
        now = utc_now()
        project.deleted_at = now
        project.updated_at = now
        project.version += 1
        self.db.commit()
        self.db.refresh(project)
        return project
