from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.volume import VolumeCreate, VolumeRead, VolumeUpdate
from app.services.volume_service import (
    VolumeNotFoundError,
    VolumeProjectNotFoundError,
    VolumeService,
)


router = APIRouter(tags=["volumes"])


def get_volume_service(db: Session = Depends(get_db)) -> VolumeService:
    return VolumeService(db)


@router.get("/api/projects/{project_id}/volumes", response_model=list[VolumeRead])
def list_project_volumes(
    project_id: str,
    service: VolumeService = Depends(get_volume_service),
):
    try:
        return service.list_project_volumes(project_id)
    except VolumeProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/volumes",
    response_model=VolumeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_volume(
    project_id: str,
    data: VolumeCreate,
    service: VolumeService = Depends(get_volume_service),
):
    try:
        return service.create_volume(project_id, data)
    except VolumeProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.patch("/api/volumes/{volume_id}", response_model=VolumeRead)
def update_volume(
    volume_id: str,
    data: VolumeUpdate,
    service: VolumeService = Depends(get_volume_service),
):
    try:
        return service.update_volume(volume_id, data)
    except VolumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Volume not found") from exc


@router.delete("/api/volumes/{volume_id}", response_model=VolumeRead)
def delete_volume(
    volume_id: str,
    service: VolumeService = Depends(get_volume_service),
):
    try:
        return service.delete_volume(volume_id)
    except VolumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Volume not found") from exc
