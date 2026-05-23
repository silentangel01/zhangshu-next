from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.project_cover_storage import (
    MAX_COVER_SIZE_BYTES,
    CoverStorageError,
    delete_project_cover_files,
    get_project_cover_media_type,
    resolve_project_cover_path,
    save_project_cover,
)
from app.schemas.project import ProjectRead
from app.services.project_service import ProjectNotFoundError, ProjectService


router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


@router.post(
    "/{project_id}/cover",
    response_model=ProjectRead,
)
async def upload_project_cover(
    project_id: str,
    file: UploadFile = File(...),
    service: ProjectService = Depends(get_project_service),
):
    try:
        service.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    content = await file.read()

    if len(content) > MAX_COVER_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="文件过大，封面图片不能超过 5MB。",
        )

    try:
        relative_path = save_project_cover(
            project_id=project_id,
            content_type=file.content_type,
            content=content,
        )
    except CoverStorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    project = service.get_project(project_id)
    old_path = project.cover_image_path
    updated = service.update_project_raw(project_id, {"cover_image_path": relative_path})

    if old_path and old_path != relative_path:
        delete_project_cover_files(old_path)

    return updated


@router.delete(
    "/{project_id}/cover",
    response_model=ProjectRead,
)
def delete_project_cover(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    try:
        project = service.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    old_path = project.cover_image_path
    delete_project_cover_files(old_path)
    return service.update_project_raw(project_id, {"cover_image_path": None})


@router.get("/{project_id}/cover")
def get_project_cover(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    try:
        project = service.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    cover_path = resolve_project_cover_path(project.cover_image_path)
    if cover_path is None:
        raise HTTPException(status_code=404, detail="No custom cover")

    media_type = get_project_cover_media_type(cover_path)
    return FileResponse(path=str(cover_path), media_type=media_type)
