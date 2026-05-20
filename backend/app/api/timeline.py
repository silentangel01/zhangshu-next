from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.timeline import (
    TimelineEventCreate,
    TimelineEventImportance,
    TimelineEventRead,
    TimelineEventStatus,
    TimelineEventType,
    TimelineEventUpdate,
)
from app.services.timeline_service import (
    TimelineChapterNotFoundError,
    TimelineChapterProjectMismatchError,
    TimelineEventNotFoundError,
    TimelineProjectNotFoundError,
    TimelineSettingNotFoundError,
    TimelineSettingProjectMismatchError,
    TimelineService,
)


router = APIRouter(tags=["timeline"])


def get_timeline_service(db: Session = Depends(get_db)) -> TimelineService:
    return TimelineService(db)


@router.get("/api/projects/{project_id}/timeline-events", response_model=list[TimelineEventRead])
def list_project_timeline_events(
    project_id: str,
    event_type: TimelineEventType | None = Query(default=None),
    status: TimelineEventStatus | None = Query(default=None),
    importance: TimelineEventImportance | None = Query(default=None),
    chapter_id: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    service: TimelineService = Depends(get_timeline_service),
):
    try:
        return service.list_project_timeline_events(
            project_id,
            event_type=event_type,
            status=status,
            importance=importance,
            chapter_id=chapter_id,
            keyword=keyword,
        )
    except TimelineProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/timeline-events",
    response_model=TimelineEventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_timeline_event(
    project_id: str,
    data: TimelineEventCreate,
    service: TimelineService = Depends(get_timeline_service),
):
    try:
        return service.create_timeline_event(project_id, data)
    except TimelineProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except TimelineChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    except TimelineChapterProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Chapter does not belong to project") from exc
    except TimelineSettingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Setting not found") from exc
    except TimelineSettingProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Setting does not belong to project") from exc


@router.get("/api/timeline-events/{event_id}", response_model=TimelineEventRead)
def get_timeline_event(event_id: str, service: TimelineService = Depends(get_timeline_service)):
    try:
        return service.get_timeline_event(event_id)
    except TimelineEventNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline event not found") from exc


@router.patch("/api/timeline-events/{event_id}", response_model=TimelineEventRead)
def update_timeline_event(
    event_id: str,
    data: TimelineEventUpdate,
    service: TimelineService = Depends(get_timeline_service),
):
    try:
        return service.update_timeline_event(event_id, data)
    except TimelineEventNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline event not found") from exc
    except TimelineChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
    except TimelineChapterProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Chapter does not belong to project") from exc
    except TimelineSettingNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Setting not found") from exc
    except TimelineSettingProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Setting does not belong to project") from exc


@router.delete("/api/timeline-events/{event_id}", response_model=TimelineEventRead)
def delete_timeline_event(event_id: str, service: TimelineService = Depends(get_timeline_service)):
    try:
        return service.delete_timeline_event(event_id)
    except TimelineEventNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline event not found") from exc


@router.get("/api/chapters/{chapter_id}/timeline-events", response_model=list[TimelineEventRead])
def list_chapter_timeline_events(
    chapter_id: str,
    service: TimelineService = Depends(get_timeline_service),
):
    try:
        return service.list_chapter_timeline_events(chapter_id)
    except TimelineChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chapter not found") from exc
