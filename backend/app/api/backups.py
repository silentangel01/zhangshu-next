from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.backup import RestoreReport
from app.services.backup_service import (
    BackupInvalidError,
    BackupProjectNotFoundError,
    BackupService,
)


router = APIRouter(prefix="/api/projects", tags=["backups"])


def get_backup_service(db: Session = Depends(get_db)) -> BackupService:
    return BackupService(db)


@router.post("/{project_id}/backup")
def export_project_backup(
    project_id: str,
    service: BackupService = Depends(get_backup_service),
):
    try:
        backup = service.export_project_backup(project_id)
    except BackupProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    headers = {"Content-Disposition": f'attachment; filename="{backup.filename}"'}
    return StreamingResponse(
        backup.content,
        media_type="application/zip",
        headers=headers,
    )


@router.post("/backup/restore", response_model=RestoreReport)
async def restore_project_backup(
    file: UploadFile = File(...),
    service: BackupService = Depends(get_backup_service),
):
    content = await file.read()
    try:
        return service.restore_project_backup(content)
    except BackupInvalidError as exc:
        raise HTTPException(status_code=400, detail="恢复失败，请检查备份文件") from exc
