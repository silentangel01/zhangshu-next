from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.export import ManuscriptExportRequest
from app.services.export_service import (
    ExportNotFoundError,
    ExportService,
    ExportUnsupportedFormatError,
)


router = APIRouter(prefix="/api/projects", tags=["exports"])


def get_export_service(db: Session = Depends(get_db)) -> ExportService:
    return ExportService(db)


@router.post("/{project_id}/export")
def export_project_manuscript(
    project_id: str,
    request: ManuscriptExportRequest,
    service: ExportService = Depends(get_export_service),
):
    try:
        export_file = service.export_manuscript(project_id, request)
    except ExportNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Export target not found") from exc
    except ExportUnsupportedFormatError as exc:
        raise HTTPException(status_code=400, detail="DOCX 导出暂未支持") from exc

    headers = {"Content-Disposition": f'attachment; filename="{export_file.filename}"'}
    return StreamingResponse(
        export_file.content,
        media_type=export_file.media_type,
        headers=headers,
    )
