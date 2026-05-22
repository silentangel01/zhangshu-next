from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.material_links import (
    MaterialLinkSummary,
    OutlineCharacterLinkCreate,
    OutlineCharacterLinkRead,
    OutlineClueLinkCreate,
    OutlineClueLinkRead,
    OutlineSettingLinkCreate,
    OutlineSettingLinkRead,
    OutlineTimelineEventLinkCreate,
    OutlineTimelineEventLinkRead,
    TimelineEventCharacterLinkCreate,
    TimelineEventCharacterLinkRead,
    TimelineEventClueLinkCreate,
    TimelineEventClueLinkRead,
    TimelineEventSettingLinkCreate,
    TimelineEventSettingLinkRead,
)
from app.services.material_link_service import (
    MaterialLinkNotFoundError,
    MaterialLinkProjectMismatchError,
    MaterialLinkProjectNotFoundError,
    MaterialLinkService,
    MaterialLinkSourceNotFoundError,
    MaterialLinkTargetNotFoundError,
)


router = APIRouter(tags=["material-links"])


def get_material_link_service(db: Session = Depends(get_db)) -> MaterialLinkService:
    return MaterialLinkService(db)


def _handle_link_error(exc: Exception) -> HTTPException:
    if isinstance(exc, MaterialLinkSourceNotFoundError):
        return HTTPException(status_code=404, detail="Source material not found")
    if isinstance(exc, MaterialLinkTargetNotFoundError):
        return HTTPException(status_code=404, detail="Target material not found")
    if isinstance(exc, MaterialLinkNotFoundError):
        return HTTPException(status_code=404, detail="Material link not found")
    if isinstance(exc, MaterialLinkProjectMismatchError):
        return HTTPException(status_code=400, detail="Linked materials must belong to the same project")
    if isinstance(exc, MaterialLinkProjectNotFoundError):
        return HTTPException(status_code=404, detail="Project not found")
    return HTTPException(status_code=500, detail="Material link operation failed")


@router.get(
    "/api/timeline-events/{event_id}/characters",
    response_model=list[TimelineEventCharacterLinkRead],
)
def list_timeline_event_characters(
    event_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.list_timeline_event_characters(event_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.post(
    "/api/timeline-events/{event_id}/characters",
    response_model=TimelineEventCharacterLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def add_timeline_event_character(
    event_id: str,
    data: TimelineEventCharacterLinkCreate,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.add_timeline_event_character(event_id, data)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.delete(
    "/api/timeline-events/{event_id}/characters/{character_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_timeline_event_character(
    event_id: str,
    character_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        service.delete_timeline_event_character(event_id, character_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.get(
    "/api/timeline-events/{event_id}/settings",
    response_model=list[TimelineEventSettingLinkRead],
)
def list_timeline_event_settings(
    event_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.list_timeline_event_settings(event_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.post(
    "/api/timeline-events/{event_id}/settings",
    response_model=TimelineEventSettingLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def add_timeline_event_setting(
    event_id: str,
    data: TimelineEventSettingLinkCreate,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.add_timeline_event_setting(event_id, data)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.delete(
    "/api/timeline-events/{event_id}/settings/{setting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_timeline_event_setting(
    event_id: str,
    setting_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        service.delete_timeline_event_setting(event_id, setting_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.get(
    "/api/timeline-events/{event_id}/clues",
    response_model=list[TimelineEventClueLinkRead],
)
def list_timeline_event_clues(
    event_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.list_timeline_event_clues(event_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.post(
    "/api/timeline-events/{event_id}/clues",
    response_model=TimelineEventClueLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def add_timeline_event_clue(
    event_id: str,
    data: TimelineEventClueLinkCreate,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.add_timeline_event_clue(event_id, data)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.delete(
    "/api/timeline-events/{event_id}/clues/{clue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_timeline_event_clue(
    event_id: str,
    clue_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        service.delete_timeline_event_clue(event_id, clue_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.get("/api/outlines/{outline_item_id}/characters", response_model=list[OutlineCharacterLinkRead])
def list_outline_characters(
    outline_item_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.list_outline_characters(outline_item_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.post(
    "/api/outlines/{outline_item_id}/characters",
    response_model=OutlineCharacterLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def add_outline_character(
    outline_item_id: str,
    data: OutlineCharacterLinkCreate,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.add_outline_character(outline_item_id, data)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.delete(
    "/api/outlines/{outline_item_id}/characters/{character_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_outline_character(
    outline_item_id: str,
    character_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        service.delete_outline_character(outline_item_id, character_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.get("/api/outlines/{outline_item_id}/settings", response_model=list[OutlineSettingLinkRead])
def list_outline_settings(
    outline_item_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.list_outline_settings(outline_item_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.post(
    "/api/outlines/{outline_item_id}/settings",
    response_model=OutlineSettingLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def add_outline_setting(
    outline_item_id: str,
    data: OutlineSettingLinkCreate,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.add_outline_setting(outline_item_id, data)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.delete(
    "/api/outlines/{outline_item_id}/settings/{setting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_outline_setting(
    outline_item_id: str,
    setting_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        service.delete_outline_setting(outline_item_id, setting_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.get("/api/outlines/{outline_item_id}/clues", response_model=list[OutlineClueLinkRead])
def list_outline_clues(
    outline_item_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.list_outline_clues(outline_item_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.post(
    "/api/outlines/{outline_item_id}/clues",
    response_model=OutlineClueLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def add_outline_clue(
    outline_item_id: str,
    data: OutlineClueLinkCreate,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.add_outline_clue(outline_item_id, data)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.delete(
    "/api/outlines/{outline_item_id}/clues/{clue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_outline_clue(
    outline_item_id: str,
    clue_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        service.delete_outline_clue(outline_item_id, clue_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.get(
    "/api/outlines/{outline_item_id}/timeline-events",
    response_model=list[OutlineTimelineEventLinkRead],
)
def list_outline_timeline_events(
    outline_item_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.list_outline_timeline_events(outline_item_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.post(
    "/api/outlines/{outline_item_id}/timeline-events",
    response_model=OutlineTimelineEventLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def add_outline_timeline_event(
    outline_item_id: str,
    data: OutlineTimelineEventLinkCreate,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.add_outline_timeline_event(outline_item_id, data)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.delete(
    "/api/outlines/{outline_item_id}/timeline-events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_outline_timeline_event(
    outline_item_id: str,
    event_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        service.delete_outline_timeline_event(outline_item_id, event_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc


@router.get("/api/projects/{project_id}/material-links/summary", response_model=MaterialLinkSummary)
def get_project_material_link_summary(
    project_id: str,
    service: MaterialLinkService = Depends(get_material_link_service),
):
    try:
        return service.get_project_summary(project_id)
    except Exception as exc:
        raise _handle_link_error(exc) from exc
