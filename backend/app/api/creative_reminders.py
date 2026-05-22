from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.creative_reminder import CreativeReminderList, CreativeReminderSeverity, CreativeReminderType
from app.services.creative_reminder_service import (
    CreativeReminderProjectNotFoundError,
    CreativeReminderService,
)


router = APIRouter(tags=["creative-reminders"])


def get_creative_reminder_service(db: Session = Depends(get_db)) -> CreativeReminderService:
    return CreativeReminderService(db)


@router.get("/api/projects/{project_id}/creative-reminders", response_model=CreativeReminderList)
def list_project_creative_reminders(
    project_id: str,
    scope: str = Query(default="project"),
    chapter_id: str | None = Query(default=None),
    severity: CreativeReminderSeverity | None = Query(default=None),
    reminder_type: CreativeReminderType | None = Query(default=None),
    service: CreativeReminderService = Depends(get_creative_reminder_service),
):
    try:
        items = service.list_project_reminders(
            project_id,
            scope=scope,
            chapter_id=chapter_id,
            severity=severity,
            reminder_type=reminder_type,
        )
    except CreativeReminderProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    return {"total": len(items), "items": items}
