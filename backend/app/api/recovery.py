from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.chapter import ChapterRead
from app.schemas.recovery import RecoveryDraftCreate, RecoveryDraftRead
from app.services.recovery_service import (
    RecoveryChapterNotFoundError,
    RecoveryDraftNotFoundError,
    RecoveryService,
)


router = APIRouter(tags=["recovery"])


def get_recovery_service(db: Session = Depends(get_db)) -> RecoveryService:
    return RecoveryService(db)


@router.get("/api/chapters/{chapter_id}/recovery-drafts", response_model=list[RecoveryDraftRead])
def list_chapter_recovery_drafts(
    chapter_id: str,
    service: RecoveryService = Depends(get_recovery_service),
):
    try:
        return service.list_chapter_drafts(chapter_id)
    except RecoveryChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.post(
    "/api/chapters/{chapter_id}/recovery-drafts",
    response_model=RecoveryDraftRead,
    status_code=status.HTTP_201_CREATED,
)
def create_chapter_recovery_draft(
    chapter_id: str,
    data: RecoveryDraftCreate,
    service: RecoveryService = Depends(get_recovery_service),
):
    try:
        return service.create_or_update_draft(chapter_id, data)
    except RecoveryChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.patch("/api/recovery-drafts/{draft_id}/recover", response_model=ChapterRead)
def recover_draft(
    draft_id: str,
    service: RecoveryService = Depends(get_recovery_service),
):
    try:
        return service.recover_draft(draft_id)
    except (RecoveryDraftNotFoundError, RecoveryChapterNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Recovery draft not found") from exc


@router.delete("/api/recovery-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recovery_draft(
    draft_id: str,
    service: RecoveryService = Depends(get_recovery_service),
):
    try:
        service.delete_draft(draft_id)
    except RecoveryDraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Recovery draft not found") from exc
