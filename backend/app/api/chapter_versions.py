from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.chapter import ChapterRead
from app.schemas.chapter_version import (
    ChapterVersionDetail,
    ChapterVersionListItem,
    CreateChapterVersionRequest,
)
from app.services.chapter_service import ChapterNotFoundError
from app.services.chapter_version_service import (
    ChapterVersionMismatchError,
    ChapterVersionNotFoundError,
    ChapterVersionService,
)


router = APIRouter(tags=["chapter versions"])


def get_chapter_version_service(db: Session = Depends(get_db)) -> ChapterVersionService:
    return ChapterVersionService(db)


@router.get(
    "/api/chapters/{chapter_id}/versions",
    response_model=list[ChapterVersionListItem],
)
def list_chapter_versions(
    chapter_id: str,
    service: ChapterVersionService = Depends(get_chapter_version_service),
):
    try:
        return service.list_versions(chapter_id)
    except ChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.get(
    "/api/chapter-versions/{version_id}",
    response_model=ChapterVersionDetail,
)
def get_chapter_version(
    version_id: str,
    service: ChapterVersionService = Depends(get_chapter_version_service),
):
    try:
        return service.get_version(version_id)
    except ChapterVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter version not found") from exc


@router.post(
    "/api/chapters/{chapter_id}/versions",
    response_model=ChapterVersionDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_chapter_version(
    chapter_id: str,
    data: CreateChapterVersionRequest,
    service: ChapterVersionService = Depends(get_chapter_version_service),
):
    try:
        return service.create_snapshot(chapter_id, data)
    except ChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.post(
    "/api/chapters/{chapter_id}/restore-version/{version_id}",
    response_model=ChapterRead,
)
def restore_chapter_version(
    chapter_id: str,
    version_id: str,
    service: ChapterVersionService = Depends(get_chapter_version_service),
):
    try:
        return service.restore_version(chapter_id, version_id)
    except ChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    except ChapterVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter version not found") from exc
    except ChapterVersionMismatchError as exc:
        raise HTTPException(status_code=400, detail="Chapter version mismatch") from exc
