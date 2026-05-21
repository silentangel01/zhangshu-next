from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.search import ProjectSearchResponse
from app.services.search_service import SearchProjectNotFoundError, SearchService


router = APIRouter(prefix="/api/projects", tags=["search"])


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    return SearchService(db)


@router.get("/{project_id}/search", response_model=ProjectSearchResponse)
def search_project_chapters(
    project_id: str,
    q: str = Query(default="", max_length=100),
    service: SearchService = Depends(get_search_service),
):
    try:
        return service.search_project_chapters(project_id, q)
    except SearchProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
