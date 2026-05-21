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
projects_import_router = APIRouter(prefix="/api/projects/import", tags=["imports"])


def get_import_service(db: Session = Depends(get_db)) -> ImportService:
    return ImportService(db)


@projects_import_router.post("/preview", response_model=ImportPreviewResponse)
async def preview_project_import(
    files: list[UploadFile] = File(...),
    service: ImportService = Depends(get_import_service),
):
    file_entries = [
        (file.filename or f"import_file_{index}", await file.read())
        for index, file in enumerate(files)
    ]
    source_filename = file_entries[0][0] if len(file_entries) == 1 else "import_files"
    try:
        return service.preview_external_files(
            source_filename=source_filename,
            files=file_entries,
        )
    except ImportPreviewInvalidError as exc:
        raise HTTPException(status_code=400, detail="导入失败，请检查文件") from exc


@projects_import_router.post("/commit", response_model=ImportConfirmResponse)
def commit_project_import(
    data: ConfirmImportRequest,
    service: ImportService = Depends(get_import_service),
):
    if not data.import_id:
        raise HTTPException(status_code=400, detail="Import id is required")
    try:
        return service.confirm_import(data.import_id, data)
    except ImportPreviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="导入预览不存在") from exc
    except ImportPreviewInvalidError as exc:
        raise HTTPException(status_code=400, detail="导入预览不可导入") from exc


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
