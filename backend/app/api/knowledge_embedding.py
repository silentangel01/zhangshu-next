"""Knowledge embedding API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.dashscope_embedding_provider import (
    DashScopeApiKeyMissingError,
    DashScopeEmbeddingError,
)
from app.infrastructure.database import get_db
from app.infrastructure.embedding_provider_factory import (
    get_default_provider_id,
    list_provider_options,
)
from app.repositories.knowledge_index_profile_repo import KnowledgeIndexProfileRepository
from app.schemas.knowledge_embedding import (
    BuildSourceEmbeddingsResponse,
    EmbeddingProviderInfo,
    EmbeddingProviderListResponse,
    IndexProfileResponse,
    IndexStatusResponse,
    RebuildIndexResponse,
    RefreshKnowledgeIndexRequest,
    RefreshKnowledgeIndexResponse,
)
from app.services.knowledge_embedding_service import (
    EmbeddingProjectNotFoundError,
    KnowledgeEmbeddingService,
)
from app.services.knowledge_index_refresh_service import (
    KnowledgeIndexPrivacyRequiredError,
    KnowledgeIndexProviderConflictError,
    KnowledgeIndexProviderUnavailableError,
    KnowledgeIndexRefreshProjectNotFoundError,
    KnowledgeIndexRefreshService,
    KnowledgeIndexRefreshSourceNotFoundError,
)


router = APIRouter(tags=["knowledge-embedding"])


def get_knowledge_embedding_service(
    db: Session = Depends(get_db),
) -> KnowledgeEmbeddingService:
    return KnowledgeEmbeddingService(db)


def get_knowledge_index_refresh_service(
    db: Session = Depends(get_db),
) -> KnowledgeIndexRefreshService:
    return KnowledgeIndexRefreshService(db)


@router.post(
    "/api/projects/{project_id}/knowledge/embeddings/rebuild",
    response_model=RebuildIndexResponse,
)
def rebuild_project_embeddings(
    project_id: str,
    service: KnowledgeIndexRefreshService = Depends(get_knowledge_index_refresh_service),
) -> RebuildIndexResponse:
    """Rebuild embedding index for all chunks in a project.

    Legacy endpoint — delegates to refresh service with default provider.
    """
    try:
        result = service.refresh_project(project_id)
        return RebuildIndexResponse(
            indexed_count=result.indexed_count,
            model_name=result.model_name,
        )
    except KnowledgeIndexRefreshProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post(
    "/api/knowledge-sources/{source_id}/embeddings",
    response_model=BuildSourceEmbeddingsResponse,
)
def build_source_embeddings(
    source_id: str,
    service: KnowledgeIndexRefreshService = Depends(get_knowledge_index_refresh_service),
) -> BuildSourceEmbeddingsResponse:
    """Build embeddings for all chunks of a source.

    Legacy endpoint — delegates to refresh service with default provider.
    """
    try:
        result = service.refresh_source(source_id)
        return BuildSourceEmbeddingsResponse(
            indexed_count=result.indexed_count,
            source_id=source_id,
            model_name=result.model_name,
        )
    except KnowledgeIndexRefreshSourceNotFoundError:
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
            provider_id=status.provider_id,
            provider_type=status.provider_type,
            display_name=status.display_name,
            vector_dim=status.vector_dim,
            chunk_size=status.chunk_size,
            profile_status=status.profile_status,
            last_refreshed_at=status.last_refreshed_at,
            last_error=status.last_error,
        )
    except EmbeddingProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post(
    "/api/projects/{project_id}/knowledge/index/refresh",
    response_model=RefreshKnowledgeIndexResponse,
)
def refresh_knowledge_index(
    project_id: str,
    body: RefreshKnowledgeIndexRequest,
    service: KnowledgeIndexRefreshService = Depends(
        get_knowledge_index_refresh_service
    ),
) -> RefreshKnowledgeIndexResponse:
    """Refresh knowledge index: rebuild chunks then refresh embeddings."""
    if body.scope == "source":
        if not body.source_id:
            raise HTTPException(
                status_code=422,
                detail="source_id is required when scope is 'source'",
            )
        # Verify source belongs to the project
        source = service.knowledge_service.repo.get_source(body.source_id)
        if source is None or source.project_id != project_id:
            raise HTTPException(status_code=404, detail="Source not found")
        try:
            result = service.refresh_source(
                body.source_id,
                chunk_size=body.chunk_size,
                provider_id=body.provider_id,
                privacy_confirmed=body.privacy_confirmed,
            )
        except KnowledgeIndexRefreshSourceNotFoundError:
            raise HTTPException(status_code=404, detail="Source not found")
        except KnowledgeIndexProviderConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except KnowledgeIndexPrivacyRequiredError:
            raise HTTPException(
                status_code=403, detail="使用云端服务需确认隐私条款"
            )
        except KnowledgeIndexProviderUnavailableError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except DashScopeApiKeyMissingError:
            raise HTTPException(status_code=503, detail="API Key 未配置")
        except DashScopeEmbeddingError as exc:
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        try:
            result = service.refresh_project(
                project_id,
                chunk_size=body.chunk_size,
                provider_id=body.provider_id,
                privacy_confirmed=body.privacy_confirmed,
            )
        except KnowledgeIndexRefreshProjectNotFoundError:
            raise HTTPException(status_code=404, detail="Project not found")
        except KnowledgeIndexPrivacyRequiredError:
            raise HTTPException(
                status_code=403, detail="使用云端服务需确认隐私条款"
            )
        except KnowledgeIndexProviderUnavailableError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except DashScopeApiKeyMissingError:
            raise HTTPException(status_code=503, detail="API Key 未配置")
        except DashScopeEmbeddingError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    return RefreshKnowledgeIndexResponse(
        source_count=result.source_count,
        chunk_count=result.chunk_count,
        indexed_count=result.indexed_count,
        chunk_size=result.chunk_size,
        model_name=result.model_name,
        provider_id=result.provider_id,
        warnings=result.warnings,
    )


@router.get(
    "/api/projects/{project_id}/knowledge/embedding-providers",
    response_model=EmbeddingProviderListResponse,
)
def list_embedding_providers(
    project_id: str,
) -> EmbeddingProviderListResponse:
    """List all known embedding providers with availability status."""
    providers = list_provider_options()
    return EmbeddingProviderListResponse(
        providers=[
            EmbeddingProviderInfo(
                id=p.id,
                display_name=p.display_name,
                provider_type=p.provider_type,
                model_name=p.model_name,
                vector_dim=p.vector_dim,
                available=p.available,
                reason=p.reason,
                requires_privacy_confirm=p.requires_privacy_confirm,
                requires_network=p.requires_network,
                quality_label=p.quality_label,
                description=p.description,
            )
            for p in providers
        ],
        default_provider_id=get_default_provider_id(),
    )


@router.get(
    "/api/projects/{project_id}/knowledge/index-profile",
    response_model=IndexProfileResponse,
)
def get_index_profile(
    project_id: str,
    db: Session = Depends(get_db),
) -> IndexProfileResponse:
    """Get the current index profile for a project."""
    repo = KnowledgeIndexProfileRepository(db)
    profile = repo.get_by_project(project_id)
    if profile is None:
        return IndexProfileResponse()
    last_refreshed_str = None
    if profile.last_refreshed_at is not None:
        last_refreshed_str = profile.last_refreshed_at.isoformat()
    return IndexProfileResponse(
        provider_id=profile.provider_id,
        provider_type=profile.provider_type,
        display_name=profile.display_name,
        model_name=profile.model_name,
        vector_dim=profile.vector_dim,
        chunk_size=profile.chunk_size,
        status=profile.status,
        last_refreshed_at=last_refreshed_str,
        last_error=profile.last_error,
    )
