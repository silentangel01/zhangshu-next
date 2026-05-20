from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.clue import (
    ChapterClueCreate,
    ChapterClueRead,
    ChapterClueUpdate,
    ClueCharacterCreate,
    ClueCharacterRead,
    ClueCharacterUpdate,
    ClueCreate,
    ClueImportance,
    ClueRead,
    ClueSettingCreate,
    ClueSettingRead,
    ClueSettingUpdate,
    ClueStatus,
    ClueUpdate,
    ClueVisibility,
)
from app.services.chapter_clue_service import (
    ChapterClueChapterNotFoundError,
    ChapterClueClueNotFoundError,
    ChapterClueLinkNotFoundError,
    ChapterClueProjectMismatchError,
    ChapterClueService,
)
from app.services.clue_character_service import (
    ClueCharacterCharacterNotFoundError,
    ClueCharacterClueNotFoundError,
    ClueCharacterLinkNotFoundError,
    ClueCharacterProjectMismatchError,
    ClueCharacterService,
)
from app.services.clue_service import (
    ClueChapterNotFoundError,
    ClueChapterProjectMismatchError,
    ClueNotFoundError,
    ClueProjectNotFoundError,
    ClueService,
)
from app.services.clue_setting_service import (
    ClueSettingClueNotFoundError,
    ClueSettingItemNotFoundError,
    ClueSettingLinkNotFoundError,
    ClueSettingProjectMismatchError,
    ClueSettingService,
)


router = APIRouter(tags=["clues"])


def get_clue_service(db: Session = Depends(get_db)) -> ClueService:
    return ClueService(db)


def get_chapter_clue_service(db: Session = Depends(get_db)) -> ChapterClueService:
    return ChapterClueService(db)


def get_clue_character_service(db: Session = Depends(get_db)) -> ClueCharacterService:
    return ClueCharacterService(db)


def get_clue_setting_service(db: Session = Depends(get_db)) -> ClueSettingService:
    return ClueSettingService(db)


@router.get("/api/projects/{project_id}/clues", response_model=list[ClueRead])
def list_project_clues(
    project_id: str,
    status: ClueStatus | None = Query(default=None),
    visibility: ClueVisibility | None = Query(default=None),
    importance: ClueImportance | None = Query(default=None),
    keyword: str | None = Query(default=None),
    service: ClueService = Depends(get_clue_service),
):
    try:
        return service.list_project_clues(
            project_id,
            status=status,
            visibility=visibility,
            importance=importance,
            keyword=keyword,
        )
    except ClueProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post("/api/projects/{project_id}/clues", response_model=ClueRead, status_code=status.HTTP_201_CREATED)
def create_clue(project_id: str, data: ClueCreate, service: ClueService = Depends(get_clue_service)):
    try:
        return service.create_clue(project_id, data)
    except ClueProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ClueChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    except ClueChapterProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Chapter does not belong to project") from exc


@router.get("/api/clues/{clue_id}", response_model=ClueRead)
def get_clue(clue_id: str, service: ClueService = Depends(get_clue_service)):
    try:
        return service.get_clue(clue_id)
    except ClueNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue not found") from exc


@router.patch("/api/clues/{clue_id}", response_model=ClueRead)
def update_clue(clue_id: str, data: ClueUpdate, service: ClueService = Depends(get_clue_service)):
    try:
        return service.update_clue(clue_id, data)
    except ClueNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue not found") from exc
    except ClueChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    except ClueChapterProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Chapter does not belong to project") from exc


@router.delete("/api/clues/{clue_id}", response_model=ClueRead)
def delete_clue(clue_id: str, service: ClueService = Depends(get_clue_service)):
    try:
        return service.delete_clue(clue_id)
    except ClueNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue not found") from exc


@router.get("/api/chapters/{chapter_id}/clues", response_model=list[ChapterClueRead])
def list_chapter_clues(chapter_id: str, service: ChapterClueService = Depends(get_chapter_clue_service)):
    try:
        return service.list_chapter_clues(chapter_id)
    except ChapterClueChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.post("/api/chapters/{chapter_id}/clues", response_model=ChapterClueRead, status_code=status.HTTP_201_CREATED)
def add_chapter_clue(
    chapter_id: str,
    data: ChapterClueCreate,
    service: ChapterClueService = Depends(get_chapter_clue_service),
):
    try:
        return service.add_chapter_clue(chapter_id, data)
    except ChapterClueChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    except ChapterClueClueNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue not found") from exc
    except ChapterClueProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Clue does not belong to chapter project") from exc


@router.patch("/api/chapter-clues/{link_id}", response_model=ChapterClueRead)
def update_chapter_clue(
    link_id: str,
    data: ChapterClueUpdate,
    service: ChapterClueService = Depends(get_chapter_clue_service),
):
    try:
        return service.update_chapter_clue(link_id, data)
    except ChapterClueLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter clue link not found") from exc
    except ChapterClueClueNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue not found") from exc


@router.delete("/api/chapter-clues/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter_clue(link_id: str, service: ChapterClueService = Depends(get_chapter_clue_service)):
    try:
        service.delete_chapter_clue(link_id)
    except ChapterClueLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter clue link not found") from exc


@router.get("/api/clues/{clue_id}/characters", response_model=list[ClueCharacterRead])
def list_clue_characters(clue_id: str, service: ClueCharacterService = Depends(get_clue_character_service)):
    try:
        return service.list_clue_characters(clue_id)
    except ClueCharacterClueNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue not found") from exc


@router.post("/api/clues/{clue_id}/characters", response_model=ClueCharacterRead, status_code=status.HTTP_201_CREATED)
def add_clue_character(
    clue_id: str,
    data: ClueCharacterCreate,
    service: ClueCharacterService = Depends(get_clue_character_service),
):
    try:
        return service.add_clue_character(clue_id, data)
    except ClueCharacterClueNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue not found") from exc
    except ClueCharacterCharacterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Character not found") from exc
    except ClueCharacterProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Character does not belong to clue project") from exc


@router.patch("/api/clue-characters/{link_id}", response_model=ClueCharacterRead)
def update_clue_character(
    link_id: str,
    data: ClueCharacterUpdate,
    service: ClueCharacterService = Depends(get_clue_character_service),
):
    try:
        return service.update_clue_character(link_id, data)
    except ClueCharacterLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue character link not found") from exc
    except ClueCharacterCharacterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Character not found") from exc


@router.delete("/api/clue-characters/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clue_character(link_id: str, service: ClueCharacterService = Depends(get_clue_character_service)):
    try:
        service.delete_clue_character(link_id)
    except ClueCharacterLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue character link not found") from exc


@router.get("/api/clues/{clue_id}/settings", response_model=list[ClueSettingRead])
def list_clue_settings(clue_id: str, service: ClueSettingService = Depends(get_clue_setting_service)):
    try:
        return service.list_clue_settings(clue_id)
    except ClueSettingClueNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue not found") from exc


@router.post("/api/clues/{clue_id}/settings", response_model=ClueSettingRead, status_code=status.HTTP_201_CREATED)
def add_clue_setting(
    clue_id: str,
    data: ClueSettingCreate,
    service: ClueSettingService = Depends(get_clue_setting_service),
):
    try:
        return service.add_clue_setting(clue_id, data)
    except ClueSettingClueNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue not found") from exc
    except ClueSettingItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Setting not found") from exc
    except ClueSettingProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Setting does not belong to clue project") from exc


@router.patch("/api/clue-settings/{link_id}", response_model=ClueSettingRead)
def update_clue_setting(
    link_id: str,
    data: ClueSettingUpdate,
    service: ClueSettingService = Depends(get_clue_setting_service),
):
    try:
        return service.update_clue_setting(link_id, data)
    except ClueSettingLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue setting link not found") from exc
    except ClueSettingItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Setting not found") from exc


@router.delete("/api/clue-settings/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clue_setting(link_id: str, service: ClueSettingService = Depends(get_clue_setting_service)):
    try:
        service.delete_clue_setting(link_id)
    except ClueSettingLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Clue setting link not found") from exc
