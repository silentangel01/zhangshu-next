"""Cloud project data access layer."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cloud_project import CloudProject


class CloudProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, project_id: str) -> CloudProject | None:
        return self.db.scalar(
            select(CloudProject).where(
                CloudProject.id == project_id,
                CloudProject.deleted_at.is_(None),
            )
        )

    def get_owned_by_user(
        self, project_id: str, owner_id: str
    ) -> CloudProject | None:
        return self.db.scalar(
            select(CloudProject).where(
                CloudProject.id == project_id,
                CloudProject.owner_id == owner_id,
                CloudProject.deleted_at.is_(None),
            )
        )

    def list_by_owner(self, owner_id: str) -> list[CloudProject]:
        statement = (
            select(CloudProject)
            .where(
                CloudProject.owner_id == owner_id,
                CloudProject.deleted_at.is_(None),
            )
            .order_by(CloudProject.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def count_by_owner(self, owner_id: str) -> int:
        statement = select(func.count()).select_from(
            select(CloudProject)
            .where(
                CloudProject.owner_id == owner_id,
                CloudProject.deleted_at.is_(None),
            )
            .subquery()
        )
        return self.db.scalar(statement) or 0

    def create(
        self, project: CloudProject, *, commit: bool = True
    ) -> CloudProject:
        self.db.add(project)
        if commit:
            self.db.commit()
            self.db.refresh(project)
        return project

    def update(
        self,
        project: CloudProject,
        values: dict,
        *,
        commit: bool = True,
    ) -> CloudProject:
        for key, value in values.items():
            setattr(project, key, value)
        if commit:
            self.db.commit()
            self.db.refresh(project)
        return project

    def soft_delete(
        self, project: CloudProject, *, commit: bool = True
    ) -> None:
        from app.models.user import utc_now

        project.deleted_at = utc_now()
        if commit:
            self.db.commit()
