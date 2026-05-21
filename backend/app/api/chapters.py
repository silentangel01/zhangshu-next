from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.chapter import (
    ChapterCreate,
    ChapterRead,
    ChapterReorderRequest,
    ChapterReorderResponse,
    ChapterUpdate,
)
from app.services.chapter_service import (
    ChapterNotFoundError,
    ChapterProjectNotFoundError,
    ChapterService,
    ChapterVolumeNotFoundError,
)


router = APIRouter(tags=["chapters"])


def get_chapter_service(db: Session = Depends(get_db)) -> ChapterService:
    return ChapterService(db)


@router.get("/api/projects/{project_id}/chapters", response_model=list[ChapterRead])
def list_project_chapters(
    project_id: str,
    service: ChapterService = Depends(get_chapter_service),
):
    try:
        return service.list_project_chapters(project_id)
    except ChapterProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/chapters",
    response_model=ChapterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_chapter(
    project_id: str,
    data: ChapterCreate,
    service: ChapterService = Depends(get_chapter_service),
):
    try:
        return service.create_chapter(project_id, data)
    except ChapterProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ChapterVolumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Volume not found") from exc


@router.get("/api/chapters/{chapter_id}", response_model=ChapterRead)
def get_chapter(
    chapter_id: str,
    service: ChapterService = Depends(get_chapter_service),
):
    try:
        return service.get_chapter(chapter_id)
    except ChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.patch("/api/chapters/{chapter_id}", response_model=ChapterRead)
def update_chapter(
    chapter_id: str,
    data: ChapterUpdate,
    service: ChapterService = Depends(get_chapter_service),
):
    try:
        return service.update_chapter(chapter_id, data)
    except ChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    except ChapterVolumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Volume not found") from exc


@router.patch(
    "/api/projects/{project_id}/chapters/reorder",
    response_model=ChapterReorderResponse,
)
def reorder_chapters(
    project_id: str,
    data: ChapterReorderRequest,
    service: ChapterService = Depends(get_chapter_service),
):
    try:
        updated_count, warnings = service.reorder_chapters(project_id, data)
        return ChapterReorderResponse(updated_count=updated_count, warnings=warnings)
    except ChapterProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    except ChapterVolumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Volume not found") from exc


@router.delete("/api/chapters/{chapter_id}", response_model=ChapterRead)
def delete_chapter(
    chapter_id: str,
    service: ChapterService = Depends(get_chapter_service),
):
    try:
        return service.delete_chapter(chapter_id)
    except ChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
