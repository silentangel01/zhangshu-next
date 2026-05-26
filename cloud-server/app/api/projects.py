"""Project management API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.project import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
)
from app.services.project_service import ProjectError, ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
def create_project(
    body: CreateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProjectService(db)
    try:
        project = service.create_project(current_user.id, body.title)
    except ProjectError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return ProjectResponse(
        id=project.id,
        title=project.title,
        owner_id=project.owner_id,
        created_at=project.created_at,
    )


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProjectService(db)
    projects, total = service.list_projects(current_user.id)
    items = [
        ProjectResponse(
            id=p.id,
            title=p.title,
            owner_id=p.owner_id,
            created_at=p.created_at,
        )
        for p in projects
    ]
    return ProjectListResponse(items=items, total=total)
