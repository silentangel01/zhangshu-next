from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.setting import (
    ChapterSettingCreate,
    ChapterSettingRead,
    ChapterSettingUpdate,
    SettingCanonStatus,
    SettingCreate,
    SettingImportance,
    SettingItemType,
    SettingNodeKind,
    SettingRead,
    SettingUpdate,
)
from app.services.chapter_setting_service import (
    ChapterSettingChapterNotFoundError,
    ChapterSettingItemNotFoundError,
    ChapterSettingLinkNotFoundError,
    ChapterSettingProjectMismatchError,
    ChapterSettingService,
)
from app.services.setting_service import (
    SettingFolderNotEmptyError,
    SettingInvalidNodeKindError,
    SettingInvalidParentError,
    SettingNotFoundError,
    SettingParentCycleError,
    SettingParentNotFoundError,
    SettingParentProjectMismatchError,
    SettingProjectNotFoundError,
    SettingService,
    SettingSystemFolderProtectedError,
)


router = APIRouter(tags=["settings"])


def get_setting_service(db: Session = Depends(get_db)) -> SettingService:
    return SettingService(db)


def get_chapter_setting_service(db: Session = Depends(get_db)) -> ChapterSettingService:
    return ChapterSettingService(db)


@router.get("/api/projects/{project_id}/settings", response_model=list[SettingRead])
def list_project_settings(
    project_id: str,
    item_type: SettingItemType | None = Query(default=None),
    canon_status: SettingCanonStatus | None = Query(default=None),
    importance: SettingImportance | None = Query(default=None),
    keyword: str | None = Query(default=None),
    node_kind: SettingNodeKind | None = Query(default=None),
    service: SettingService = Depends(get_setting_service),
):
    try:
        return service.list_project_settings(
            project_id,
            item_type=item_type,
            canon_status=canon_status,
            importance=importance,
            keyword=keyword,
            node_kind=node_kind,
        )
    except SettingProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/settings",
    response_model=SettingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_setting(
    project_id: str,
    data: SettingCreate,
    service: SettingService = Depends(get_setting_service),
):
    try:
        return service.create_setting(project_id, data)
    except SettingProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except SettingParentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Parent setting not found") from exc
    except SettingParentProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Parent setting does not belong to project") from exc
    except SettingInvalidParentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SettingParentCycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/settings/{setting_id}", response_model=SettingRead)
def get_setting(
    setting_id: str,
    service: SettingService = Depends(get_setting_service),
):
    try:
        return service.get_setting(setting_id)
    except SettingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Setting not found") from exc


@router.patch("/api/settings/{setting_id}", response_model=SettingRead)
def update_setting(
    setting_id: str,
    data: SettingUpdate,
    service: SettingService = Depends(get_setting_service),
):
    try:
        return service.update_setting(setting_id, data)
    except SettingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Setting not found") from exc
    except SettingParentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Parent setting not found") from exc
    except SettingParentProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Parent setting does not belong to project") from exc
    except SettingInvalidNodeKindError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SettingInvalidParentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SettingParentCycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/settings/{setting_id}", response_model=SettingRead)
def delete_setting(
    setting_id: str,
    service: SettingService = Depends(get_setting_service),
):
    try:
        return service.delete_setting(setting_id)
    except SettingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Setting not found") from exc
    except SettingSystemFolderProtectedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SettingFolderNotEmptyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/chapters/{chapter_id}/settings", response_model=list[ChapterSettingRead])
def list_chapter_settings(
    chapter_id: str,
    service: ChapterSettingService = Depends(get_chapter_setting_service),
):
    try:
        return service.list_chapter_settings(chapter_id)
    except ChapterSettingChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc


@router.post(
    "/api/chapters/{chapter_id}/settings",
    response_model=ChapterSettingRead,
    status_code=status.HTTP_201_CREATED,
)
def add_chapter_setting(
    chapter_id: str,
    data: ChapterSettingCreate,
    service: ChapterSettingService = Depends(get_chapter_setting_service),
):
    try:
        return service.add_chapter_setting(chapter_id, data)
    except ChapterSettingChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    except ChapterSettingItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Setting not found") from exc
    except ChapterSettingProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Setting does not belong to chapter project") from exc


@router.patch("/api/chapter-settings/{link_id}", response_model=ChapterSettingRead)
def update_chapter_setting(
    link_id: str,
    data: ChapterSettingUpdate,
    service: ChapterSettingService = Depends(get_chapter_setting_service),
):
    try:
        return service.update_chapter_setting(link_id, data)
    except ChapterSettingLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter setting link not found") from exc
    except ChapterSettingItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Setting not found") from exc


@router.delete("/api/chapter-settings/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter_setting(
    link_id: str,
    service: ChapterSettingService = Depends(get_chapter_setting_service),
):
    try:
        service.delete_chapter_setting(link_id)
    except ChapterSettingLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter setting link not found") from exc
