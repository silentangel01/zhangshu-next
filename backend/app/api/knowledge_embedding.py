"""Knowledge embedding API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.knowledge_embedding import (
    BuildSourceEmbeddingsResponse,
    IndexStatusResponse,
    RebuildIndexResponse,
)
from app.services.knowledge_embedding_service import (
    EmbeddingProjectNotFoundError,
    EmbeddingSourceNotFoundError,
    KnowledgeEmbeddingService,
)


router = APIRouter(tags=["knowledge-embedding"])


def get_knowledge_embedding_service(
    db: Session = Depends(get_db),
) -> KnowledgeEmbeddingService:
    return KnowledgeEmbeddingService(db)


@router.post(
    "/api/projects/{project_id}/knowledge/embeddings/rebuild",
    response_model=RebuildIndexResponse,
)
def rebuild_project_embeddings(
    project_id: str,
    service: KnowledgeEmbeddingService = Depends(get_knowledge_embedding_service),
) -> RebuildIndexResponse:
    """Rebuild embedding index for all chunks in a project."""
    try:
        count = service.rebuild_project_index(project_id)
        return RebuildIndexResponse(
            indexed_count=count,
            model_name=service.provider.model_name,
        )
    except EmbeddingProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post(
    "/api/knowledge-sources/{source_id}/embeddings",
    response_model=BuildSourceEmbeddingsResponse,
)
def build_source_embeddings(
    source_id: str,
    service: KnowledgeEmbeddingService = Depends(get_knowledge_embedding_service),
) -> BuildSourceEmbeddingsResponse:
    """Build embeddings for all chunks of a source."""
    try:
        count = service.index_source(source_id)
        # Get source to retrieve project_id
        source = service._get_active_source(source_id)
        return BuildSourceEmbeddingsResponse(
            indexed_count=count,
            source_id=source_id,
            model_name=service.provider.model_name,
        )
    except EmbeddingSourceNotFoundError:
        raise HTTPException(status_code=404, detail="Source not found")


@router.get(
    "/api/projects/{project_id}/knowledge/embeddings/status",
    response_model=IndexStatusResponse,
)
def get_embedding_status(
    project_id: str,
    service: KnowledgeEmbeddingService = Depends(get_knowledge_embedding_service),
) -> IndexStatusResponse:
    """Get embedding index status for a project."""
    try:
        status = service.get_index_status(project_id)
        return IndexStatusResponse(
            total_chunks=status.total_chunks,
            indexed_chunks=status.indexed_chunks,
            unindexed_chunks=status.unindexed_chunks,
            model_name=status.model_name,
        )
    except EmbeddingProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
