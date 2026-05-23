from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.knowledge_retrieval import KnowledgeRetrievalResponse
from app.services.knowledge_retrieval_service import (
    KnowledgeRetrievalProjectNotFoundError,
)
from app.services.retrieval_service import (
    RetrievalInvalidModeError,
    RetrievalProjectNotFoundError,
    RetrievalService,
)


router = APIRouter(tags=["knowledge-retrieval"])


def get_retrieval_service(
    db: Session = Depends(get_db),
) -> RetrievalService:
    return RetrievalService(db)


@router.get(
    "/api/projects/{project_id}/knowledge/search",
    response_model=KnowledgeRetrievalResponse,
)
def search_knowledge_chunks(
    project_id: str,
    keyword: str = Query(..., min_length=1),
    source_type: str | None = Query(default=None),
    credibility: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    mode: str = Query(
        default="keyword",
        description="Search mode: keyword, semantic, or hybrid",
    ),
    service: RetrievalService = Depends(get_retrieval_service),
):
    """Search knowledge chunks with keyword, semantic, or hybrid mode.

    Modes:
    - keyword: Traditional ILIKE text matching with context extraction
    - semantic: Vector similarity search using chunk embeddings
    - hybrid: Combined keyword + semantic results, deduplicated

    Returns matched chunks with:
    - Matched snippet and surrounding context
    - Source title, type, credibility for citation
    - Chunk heading and index for reference location
    - Relevance score (semantic/hybrid modes only)
    """
    try:
        return service.search(
            project_id,
            keyword,
            mode=mode,
            source_type=source_type,
            credibility=credibility,
            tag=tag,
            source_id=source_id,
            limit=limit,
        )
    except RetrievalProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except KnowledgeRetrievalProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except RetrievalInvalidModeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
