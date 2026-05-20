from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.outline import (
    OutlineItemCreate,
    OutlineItemRead,
    OutlineItemType,
    OutlineItemUpdate,
    OutlineStatus,
)
from app.services.outline_service import (
    OutlineChapterNotFoundError,
    OutlineInvalidParentError,
    OutlineNotFoundError,
    OutlineParentNotFoundError,
    OutlineProjectNotFoundError,
    OutlineService,
    OutlineVolumeNotFoundError,
)


router = APIRouter(tags=["outlines"])


def get_outline_service(db: Session = Depends(get_db)) -> OutlineService:
    return OutlineService(db)


@router.get("/api/projects/{project_id}/outlines", response_model=list[OutlineItemRead])
def list_project_outlines(
    project_id: str,
    volume_id: str | None = Query(default=None),
    chapter_id: str | None = Query(default=None),
    item_type: OutlineItemType | None = Query(default=None),
    status: OutlineStatus | None = Query(default=None),
    service: OutlineService = Depends(get_outline_service),
):
    try:
        return service.list_project_outlines(
            project_id,
            volume_id=volume_id,
            chapter_id=chapter_id,
            item_type=item_type,
            status=status,
        )
    except OutlineProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/outlines",
    response_model=OutlineItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_outline(
    project_id: str,
    data: OutlineItemCreate,
    service: OutlineService = Depends(get_outline_service),
):
    try:
        return service.create_outline(project_id, data)
    except OutlineProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except OutlineParentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Parent outline not found") from exc
    except OutlineVolumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Volume not found") from exc
    except OutlineChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.get("/api/outlines/{outline_id}", response_model=OutlineItemRead)
def get_outline(
    outline_id: str,
    service: OutlineService = Depends(get_outline_service),
):
    try:
        return service.get_outline(outline_id)
    except OutlineNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Outline not found") from exc


@router.patch("/api/outlines/{outline_id}", response_model=OutlineItemRead)
def update_outline(
    outline_id: str,
    data: OutlineItemUpdate,
    service: OutlineService = Depends(get_outline_service),
):
    try:
        return service.update_outline(outline_id, data)
    except OutlineNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Outline not found") from exc
    except OutlineInvalidParentError as exc:
        raise HTTPException(status_code=400, detail="Outline cannot be its own parent") from exc
    except OutlineParentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Parent outline not found") from exc
    except OutlineVolumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Volume not found") from exc
    except OutlineChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.delete("/api/outlines/{outline_id}", response_model=OutlineItemRead)
def delete_outline(
    outline_id: str,
    service: OutlineService = Depends(get_outline_service),
):
    try:
        return service.delete_outline(outline_id)
    except OutlineNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Outline not found") from exc


@router.get("/api/chapters/{chapter_id}/outlines", response_model=list[OutlineItemRead])
def list_chapter_outlines(
    chapter_id: str,
    service: OutlineService = Depends(get_outline_service),
):
    try:
        return service.list_chapter_outlines(chapter_id)
    except OutlineChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.get("/api/volumes/{volume_id}/outlines", response_model=list[OutlineItemRead])
def list_volume_outlines(
    volume_id: str,
    service: OutlineService = Depends(get_outline_service),
):
    try:
        return service.list_volume_outlines(volume_id)
    except OutlineVolumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Volume not found") from exc
