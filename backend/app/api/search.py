from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.search import ProjectSearchResponse, RebuildSearchIndexResponse
from app.services.search_service import SearchProjectNotFoundError, SearchService


router = APIRouter(prefix="/api/projects", tags=["search"])


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    return SearchService(db)


@router.get("/{project_id}/search", response_model=ProjectSearchResponse)
def search_project(
    project_id: str,
    q: str = Query(default="", max_length=100),
    types: str | None = Query(default=None, description="Comma-separated entity types"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: SearchService = Depends(get_search_service),
):
    entity_types: list[str] | None = None
    if types:
        entity_types = [t.strip() for t in types.split(",") if t.strip()]

    try:
        return service.search(
            project_id=project_id,
            query=q,
            entity_types=entity_types,
            limit=limit,
            offset=offset,
        )
    except SearchProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/{project_id}/search-index/rebuild",
    response_model=RebuildSearchIndexResponse,
)
def rebuild_search_index(
    project_id: str,
    service: SearchService = Depends(get_search_service),
):
    try:
        count = service.rebuild_search_index(project_id)
    except SearchProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    return RebuildSearchIndexResponse(
        project_id=project_id,
        indexed_count=count,
        message=f"搜索索引已刷新，共索引 {count} 条记录",
    )
