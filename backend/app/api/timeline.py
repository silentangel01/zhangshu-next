from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.timeline import (
    TimelineEdgeCreate,
    TimelineEdgeLineStyle,
    TimelineEdgeRead,
    TimelineEdgeType,
    TimelineEdgeUpdate,
    TimelineEdgeVisibility,
    TimelineEventCreate,
    TimelineEventImportance,
    TimelineEventRead,
    TimelineEventStatus,
    TimelineEventType,
    TimelineEventUpdate,
    TimelineTrackCreate,
    TimelineTrackRead,
    TimelineTrackUpdate,
)
from app.services.timeline_edge_service import (
    TimelineEdgeEventNotFoundError,
    TimelineEdgeEventProjectMismatchError,
    TimelineEdgeNotFoundError,
    TimelineEdgeProjectNotFoundError,
    TimelineEdgeSelfReferenceError,
    TimelineEdgeService,
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
from app.services.timeline_track_service import (
    TimelineProjectNotFoundError as TimelineTrackProjectNotFoundError,
    TimelineTrackHasEventsError,
    TimelineTrackMainRequiredError,
    TimelineTrackNotFoundError,
    TimelineTrackProjectMismatchError,
    TimelineTrackService,
)


router = APIRouter(tags=["timeline"])


def get_timeline_service(db: Session = Depends(get_db)) -> TimelineService:
    return TimelineService(db)


def get_timeline_track_service(db: Session = Depends(get_db)) -> TimelineTrackService:
    return TimelineTrackService(db)


def get_timeline_edge_service(db: Session = Depends(get_db)) -> TimelineEdgeService:
    return TimelineEdgeService(db)


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
    except TimelineTrackNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Track not found") from exc
    except TimelineTrackProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Track does not belong to project") from exc


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
    except TimelineTrackNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Track not found") from exc
    except TimelineTrackProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Track does not belong to project") from exc


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


@router.get("/api/projects/{project_id}/timeline-tracks", response_model=list[TimelineTrackRead])
def list_project_timeline_tracks(
    project_id: str,
    service: TimelineTrackService = Depends(get_timeline_track_service),
):
    try:
        return service.list_project_timeline_tracks(project_id)
    except TimelineTrackProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/timeline-tracks",
    response_model=TimelineTrackRead,
    status_code=status.HTTP_201_CREATED,
)
def create_timeline_track(
    project_id: str,
    data: TimelineTrackCreate,
    service: TimelineTrackService = Depends(get_timeline_track_service),
):
    try:
        return service.create_timeline_track(project_id, data)
    except TimelineTrackProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.get("/api/timeline-tracks/{track_id}", response_model=TimelineTrackRead)
def get_timeline_track(track_id: str, service: TimelineTrackService = Depends(get_timeline_track_service)):
    try:
        return service.get_timeline_track(track_id)
    except TimelineTrackNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline track not found") from exc


@router.patch("/api/timeline-tracks/{track_id}", response_model=TimelineTrackRead)
def update_timeline_track(
    track_id: str,
    data: TimelineTrackUpdate,
    service: TimelineTrackService = Depends(get_timeline_track_service),
):
    try:
        return service.update_timeline_track(track_id, data)
    except TimelineTrackNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline track not found") from exc
    except TimelineTrackMainRequiredError as exc:
        raise HTTPException(status_code=400, detail="Cannot remove the only main timeline track") from exc


@router.delete("/api/timeline-tracks/{track_id}", response_model=TimelineTrackRead)
def delete_timeline_track(
    track_id: str,
    service: TimelineTrackService = Depends(get_timeline_track_service),
):
    try:
        return service.delete_timeline_track(track_id)
    except TimelineTrackNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline track not found") from exc
    except TimelineTrackHasEventsError as exc:
        raise HTTPException(status_code=400, detail="Timeline track still has events") from exc
    except TimelineTrackMainRequiredError as exc:
        raise HTTPException(status_code=400, detail="Cannot delete the only main timeline track") from exc


@router.get("/api/projects/{project_id}/timeline-edges", response_model=list[TimelineEdgeRead])
def list_project_timeline_edges(
    project_id: str,
    edge_type: TimelineEdgeType | None = Query(default=None),
    visibility: TimelineEdgeVisibility | None = Query(default=None),
    service: TimelineEdgeService = Depends(get_timeline_edge_service),
):
    try:
        return service.list_project_timeline_edges(
            project_id,
            edge_type=edge_type,
            visibility=visibility,
        )
    except TimelineEdgeProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/timeline-edges",
    response_model=TimelineEdgeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_timeline_edge(
    project_id: str,
    data: TimelineEdgeCreate,
    service: TimelineEdgeService = Depends(get_timeline_edge_service),
):
    try:
        return service.create_timeline_edge(project_id, data)
    except TimelineEdgeProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except TimelineEdgeEventNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline event not found") from exc
    except TimelineEdgeEventProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Timeline event does not belong to project") from exc
    except TimelineEdgeSelfReferenceError as exc:
        raise HTTPException(status_code=400, detail="Edge cannot connect the same event") from exc


@router.get("/api/timeline-edges/{edge_id}", response_model=TimelineEdgeRead)
def get_timeline_edge(edge_id: str, service: TimelineEdgeService = Depends(get_timeline_edge_service)):
    try:
        return service.get_timeline_edge(edge_id)
    except TimelineEdgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline edge not found") from exc


@router.patch("/api/timeline-edges/{edge_id}", response_model=TimelineEdgeRead)
def update_timeline_edge(
    edge_id: str,
    data: TimelineEdgeUpdate,
    service: TimelineEdgeService = Depends(get_timeline_edge_service),
):
    try:
        return service.update_timeline_edge(edge_id, data)
    except TimelineEdgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline edge not found") from exc
    except TimelineEdgeEventNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline event not found") from exc
    except TimelineEdgeEventProjectMismatchError as exc:
        raise HTTPException(status_code=400, detail="Timeline event does not belong to project") from exc
    except TimelineEdgeSelfReferenceError as exc:
        raise HTTPException(status_code=400, detail="Edge cannot connect the same event") from exc


@router.delete("/api/timeline-edges/{edge_id}", response_model=TimelineEdgeRead)
def delete_timeline_edge(
    edge_id: str,
    service: TimelineEdgeService = Depends(get_timeline_edge_service),
):
    try:
        return service.delete_timeline_edge(edge_id)
    except TimelineEdgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Timeline edge not found") from exc
