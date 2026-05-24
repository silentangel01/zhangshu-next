from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.knowledge import (
    KnowledgeChunkRead,
    KnowledgeCredibility,
    KnowledgeImportPreviewResponse,
    KnowledgeImportResultResponse,
    KnowledgeLinkCreate,
    KnowledgeLinkRead,
    KnowledgeSourceCreate,
    KnowledgeSourceList,
    KnowledgeSourceRead,
    KnowledgeSourceStatus,
    KnowledgeSourceType,
    KnowledgeSourceUpdate,
)
from app.services.knowledge_import_service import (
    KnowledgeImportEmptyError,
    KnowledgeImportLimitError,
    KnowledgeImportProjectNotFoundError,
    KnowledgeImportService,
)
from app.services.knowledge_service import (
    KnowledgeChunkNotFoundError,
    KnowledgeLinkNotFoundError,
    KnowledgeProjectNotFoundError,
    KnowledgeService,
    KnowledgeSourceNotFoundError,
)


router = APIRouter(tags=["knowledge"])


def get_knowledge_service(db: Session = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(db)


def get_knowledge_import_service(db: Session = Depends(get_db)) -> KnowledgeImportService:
    return KnowledgeImportService(db)


@router.get(
    "/api/projects/{project_id}/knowledge-sources",
    response_model=KnowledgeSourceList,
)
def list_knowledge_sources(
    project_id: str,
    keyword: str | None = Query(default=None),
    source_type: KnowledgeSourceType | None = Query(default=None),
    source_status: KnowledgeSourceStatus | None = Query(default=None, alias="status"),
    tag: str | None = Query(default=None),
    credibility: KnowledgeCredibility | None = Query(default=None),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        items = service.list_sources(
            project_id,
            keyword=keyword,
            source_type=source_type,
            status=source_status,
            tag=tag,
            credibility=credibility,
        )
        return KnowledgeSourceList(total=len(items), items=items)
    except KnowledgeProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/knowledge-sources",
    response_model=KnowledgeSourceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_source(
    project_id: str,
    data: KnowledgeSourceCreate,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.create_source(project_id, data)
    except KnowledgeProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.get(
    "/api/knowledge-sources/{source_id}",
    response_model=KnowledgeSourceRead,
)
def get_knowledge_source(
    source_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.get_source(source_id)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge source not found") from exc


@router.patch(
    "/api/knowledge-sources/{source_id}",
    response_model=KnowledgeSourceRead,
)
def update_knowledge_source(
    source_id: str,
    data: KnowledgeSourceUpdate,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.update_source(source_id, data)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge source not found") from exc


@router.delete(
    "/api/knowledge-sources/{source_id}",
    response_model=KnowledgeSourceRead,
)
def delete_knowledge_source(
    source_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.delete_source(source_id)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge source not found") from exc


@router.get(
    "/api/knowledge-sources/{source_id}/chunks",
    response_model=list[KnowledgeChunkRead],
)
def list_knowledge_chunks(
    source_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.list_chunks(source_id)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge source not found") from exc


@router.post(
    "/api/knowledge-sources/{source_id}/rebuild-chunks",
    response_model=list[KnowledgeChunkRead],
)
def rebuild_knowledge_chunks(
    source_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.rebuild_chunks(source_id)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge source not found") from exc


@router.get(
    "/api/knowledge-sources/{source_id}/links",
    response_model=list[KnowledgeLinkRead],
)
def list_knowledge_links(
    source_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.list_links(source_id)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge source not found") from exc


@router.post(
    "/api/knowledge-sources/{source_id}/links",
    response_model=KnowledgeLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_link(
    source_id: str,
    data: KnowledgeLinkCreate,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.create_link(source_id, data)
    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge source not found") from exc
    except KnowledgeChunkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge chunk not found") from exc


@router.delete(
    "/api/knowledge-links/{link_id}",
    response_model=KnowledgeLinkRead,
)
def delete_knowledge_link(
    link_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        return service.delete_link(link_id)
    except KnowledgeLinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge link not found") from exc


# --- Knowledge Import ---


@router.post(
    "/api/projects/{project_id}/knowledge/import/preview",
    response_model=KnowledgeImportPreviewResponse,
)
def preview_knowledge_import(
    project_id: str,
    files: list[UploadFile] = File(...),
    service: KnowledgeImportService = Depends(get_knowledge_import_service),
):
    file_entries = []
    for upload_file in files:
        content = upload_file.file.read()
        file_entries.append((upload_file.filename or "unknown", content))

    try:
        return service.preview_import(file_entries)
    except KnowledgeImportLimitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/projects/{project_id}/knowledge/import/confirm",
    response_model=KnowledgeImportResultResponse,
)
def confirm_knowledge_import(
    project_id: str,
    files: list[UploadFile] = File(...),
    source_type: str = Query(default="file"),
    credibility: KnowledgeCredibility = Query(default="normal"),
    tags: str = Query(default=""),
    service: KnowledgeImportService = Depends(get_knowledge_import_service),
):
    file_entries = []
    for upload_file in files:
        content = upload_file.file.read()
        file_entries.append((upload_file.filename or "unknown", content))

    try:
        return service.confirm_import(
            project_id,
            file_entries,
            source_type=source_type,
            credibility=credibility,
            tags=tags,
        )
    except KnowledgeImportProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except KnowledgeImportEmptyError as exc:
        raise HTTPException(status_code=400, detail="没有可导入的文件") from exc
    except KnowledgeImportLimitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
