from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import ProjectNotFoundError, ProjectService


router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


@router.get("", response_model=list[ProjectRead])
def list_projects(service: ProjectService = Depends(get_project_service)):
    return service.list_projects()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
):
    return service.create_project(data)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    try:
        return service.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str,
    data: ProjectUpdate,
    service: ProjectService = Depends(get_project_service),
):
    try:
        return service.update_project(project_id, data)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.delete("/{project_id}", response_model=ProjectRead)
def delete_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    try:
        return service.delete_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
