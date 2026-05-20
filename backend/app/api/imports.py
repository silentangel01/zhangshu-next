from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.imports import ConfirmImportRequest, ImportConfirmResponse, ImportPreviewResponse, ImportType
from app.services.import_service import (
    ImportPreviewInvalidError,
    ImportPreviewNotFoundError,
    ImportService,
)


router = APIRouter(prefix="/api/imports", tags=["imports"])


def get_import_service(db: Session = Depends(get_db)) -> ImportService:
    return ImportService(db)


@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_import(
    import_type: ImportType = Form(...),
    file: UploadFile = File(...),
    service: ImportService = Depends(get_import_service),
):
    content = await file.read()
    try:
        return service.preview_import(
            import_type=import_type,
            source_filename=file.filename or "import_file",
            content=content,
        )
    except ImportPreviewInvalidError as exc:
        raise HTTPException(status_code=400, detail="导入文件无法解析") from exc


@router.post("/{import_id}/confirm", response_model=ImportConfirmResponse)
def confirm_import(
    import_id: str,
    data: ConfirmImportRequest,
    service: ImportService = Depends(get_import_service),
):
    try:
        return service.confirm_import(import_id, data)
    except ImportPreviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="导入预览不存在") from exc
    except ImportPreviewInvalidError as exc:
        raise HTTPException(status_code=400, detail="导入预览不可导入") from exc
