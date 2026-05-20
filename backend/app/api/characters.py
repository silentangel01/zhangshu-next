from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.character import (
    ChapterCharacterCreate,
    ChapterCharacterRead,
    ChapterCharacterUpdate,
    CharacterCreate,
    CharacterImportance,
    CharacterRead,
    CharacterRole,
    CharacterStatus,
    CharacterUpdate,
)
from app.services.chapter_character_service import (
    ChapterCharacterChapterNotFoundError,
    ChapterCharacterCharacterNotFoundError,
    ChapterCharacterLinkNotFoundError,
    ChapterCharacterProjectMismatchError,
    ChapterCharacterService,
)
from app.services.character_service import (
    CharacterNotFoundError,
    CharacterProjectNotFoundError,
    CharacterService,
)


router = APIRouter(tags=["characters"])


def get_character_service(db: Session = Depends(get_db)) -> CharacterService:
    return CharacterService(db)


def get_chapter_character_service(db: Session = Depends(get_db)) -> ChapterCharacterService:
    return ChapterCharacterService(db)


@router.get("/api/projects/{project_id}/characters", response_model=list[CharacterRead])
def list_project_characters(
    project_id: str,
    role: CharacterRole | None = Query(default=None),
    importance: CharacterImportance | None = Query(default=None),
    status: CharacterStatus | None = Query(default=None),
    keyword: str | None = Query(default=None),
    service: CharacterService = Depends(get_character_service),
):
    try:
        return service.list_project_characters(
            project_id,
            role=role,
            importance=importance,
            status=status,
            keyword=keyword,
        )
    except CharacterProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/characters",
    response_model=CharacterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_character(
    project_id: str,
    data: CharacterCreate,
    service: CharacterService = Depends(get_character_service),
):
    try:
        return service.create_character(project_id, data)
    except CharacterProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.get("/api/characters/{character_id}", response_model=CharacterRead)
def get_character(
    character_id: str,
    service: CharacterService = Depends(get_character_service),
):
    try:
        return service.get_character(character_id)
    except CharacterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Character not found") from exc


@router.patch("/api/characters/{character_id}", response_model=CharacterRead)
def update_character(
    character_id: str,
    data: CharacterUpdate,
    service: CharacterService = Depends(get_character_service),
):
    try:
        return service.update_character(character_id, data)
    except CharacterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Character not found") from exc


@router.delete("/api/characters/{character_id}", response_model=CharacterRead)
def delete_character(
    character_id: str,
    service: CharacterService = Depends(get_character_service),
):
    try:
        return service.delete_character(character_id)
    except CharacterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Character not found") from exc


@router.get("/api/chapters/{chapter_id}/characters", response_model=list[ChapterCharacterRead])
def list_chapter_characters(
    chapter_id: str,
    service: ChapterCharacterService = Depends(get_chapter_character_service),
):
    try:
        return service.list_chapter_characters(chapter_id)
    except ChapterCharacterChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.post(
    "/api/chapters/{chapter_id}/characters",
    response_model=ChapterCharacterRead,
    status_code=status.HTTP_201_CREATED,
)
def add_chapter_character(
    chapter_id: str,
    data: ChapterCharacterCreate,
    service: ChapterCharacterService = Depends(get_chapter_character_service),
):
    try:
        return service.add_chapter_character(chapter_id, data)
    except ChapterCharacterChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    except ChapterCharacterCharacterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Character not found") from exc
    except ChapterCharacterProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Character does not belong to chapter project") from exc


@router.patch("/api/chapter-characters/{link_id}", response_model=ChapterCharacterRead)
def update_chapter_character(
    link_id: str,
    data: ChapterCharacterUpdate,
    service: ChapterCharacterService = Depends(get_chapter_character_service),
):
    try:
        return service.update_chapter_character(link_id, data)
    except ChapterCharacterLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter character link not found") from exc
    except ChapterCharacterCharacterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Character not found") from exc


@router.delete("/api/chapter-characters/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter_character(
    link_id: str,
    service: ChapterCharacterService = Depends(get_chapter_character_service),
):
    try:
        service.delete_chapter_character(link_id)
    except ChapterCharacterLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter character link not found") from exc
