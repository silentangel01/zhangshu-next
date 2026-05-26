"""Project management service."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.cloud_project import CloudProject
from app.repositories.cloud_project_repo import CloudProjectRepository


class ProjectError(Exception):
    """Raised for project operation failures."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class ProjectService:
    def __init__(self, db: Session):
        self._repo = CloudProjectRepository(db)

    def create_project(self, owner_id: str, title: str) -> CloudProject:
        cleaned = title.strip()
        if not cleaned:
            raise ProjectError("项目名称不能为空。")
        if len(cleaned) > 200:
            raise ProjectError("项目名称不得超过 200 个字符。")

        project = CloudProject(
            id=str(uuid4()),
            owner_id=owner_id,
            title=cleaned,
        )
        return self._repo.create(project)

    def list_projects(self, owner_id: str) -> tuple[list[CloudProject], int]:
        projects = self._repo.list_by_owner(owner_id)
        total = self._repo.count_by_owner(owner_id)
        return projects, total

    def get_project_for_user(
        self, project_id: str, owner_id: str
    ) -> CloudProject:
        project = self._repo.get_owned_by_user(project_id, owner_id)
        if project is None:
            raise ProjectError("项目不存在。", status_code=404)
        return project
