from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.imports import ConfirmImportRequest, ImportConfirmResponse, ImportPreviewResponse, ImportType
from app.schemas.project_package_import import (
    ProjectPackageImportConfirmRequest,
    ProjectPackageImportConfirmResponse,
    ProjectPackageImportPreviewResponse,
)
from app.services.backup_service import BackupInvalidError
from app.services.import_service import (
    ImportPreviewInvalidError,
    ImportPreviewNotFoundError,
    ImportService,
)
from app.services.project_package_import_service import (
    ProjectPackageImportService,
    ProjectPackagePreviewNotFoundError,
)


router = APIRouter(prefix="/api/imports", tags=["imports"])
projects_import_router = APIRouter(prefix="/api/projects/import", tags=["imports"])


def get_import_service(db: Session = Depends(get_db)) -> ImportService:
    return ImportService(db)


def get_package_import_service(db: Session = Depends(get_db)) -> ProjectPackageImportService:
    return ProjectPackageImportService(db)


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


@router.post(
    "/project-package/preview",
    response_model=ProjectPackageImportPreviewResponse,
)
async def preview_project_package_import(
    file: UploadFile = File(...),
    service: ProjectPackageImportService = Depends(get_package_import_service),
):
    content = await file.read()
    try:
        return service.preview_package(content)
    except BackupInvalidError as exc:
        raise HTTPException(
            status_code=400, detail="无效的章枢项目包，请检查文件格式"
        ) from exc


@router.post(
    "/project-package/confirm",
    response_model=ProjectPackageImportConfirmResponse,
)
def confirm_project_package_import(
    data: ProjectPackageImportConfirmRequest,
    service: ProjectPackageImportService = Depends(get_package_import_service),
):
    try:
        return service.confirm_package(data.preview_id)
    except ProjectPackagePreviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="导入预览不存在或已过期") from exc
    except BackupInvalidError as exc:
        raise HTTPException(
            status_code=400, detail="无效的章枢项目包，请检查文件格式"
        ) from exc


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
