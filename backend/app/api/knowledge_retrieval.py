from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.dashscope_embedding_provider import (
    DashScopeApiKeyMissingError,
    DashScopeEmbeddingError,
)
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

_ValidStrictness = Literal["strict", "balanced", "broad"]


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
    limit: int = Query(default=20, ge=1, le=200),
    mode: str = Query(
        default="keyword",
        description="Search mode: keyword, semantic, or hybrid",
    ),
    strictness: _ValidStrictness = Query(
        default="balanced",
        description="Matching strictness: strict, balanced, or broad",
    ),
    service: RetrievalService = Depends(get_retrieval_service),
):
    """Search knowledge chunks with keyword, semantic, or hybrid mode.

    Modes:
    - keyword: Text matching with quality-aware ranking
    - semantic: Vector similarity search with quality filtering
    - hybrid: Combined keyword + semantic with unified scoring

    Strictness:
    - strict: Only highly relevant results
    - balanced: Default, good balance of relevance and recall
    - broad: Include weakly related results for exploration
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
            strictness=strictness,
        )
    except RetrievalProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except KnowledgeRetrievalProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except RetrievalInvalidModeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DashScopeApiKeyMissingError as exc:
        raise HTTPException(
            status_code=503,
            detail="Embedding 服务不可用：API Key 未配置。请切换到本地模型或配置 API Key。",
        ) from exc
    except DashScopeEmbeddingError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Embedding 云服务调用失败：{exc}",
        ) from exc
