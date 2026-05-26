from typing import Literal

from pydantic import BaseModel

KnowledgeRefreshScope = Literal["project", "source"]
KnowledgeChunkSizeField = Literal["small", "medium", "large"]
EmbeddingProviderType = Literal["local", "cloud", "compat"]


class IndexStatusResponse(BaseModel):
    """Embedding index status for a project."""

    total_chunks: int
    indexed_chunks: int
    unindexed_chunks: int
    model_name: str
    provider_id: str | None = None
    provider_type: str | None = None
    display_name: str | None = None
    vector_dim: int | None = None
    chunk_size: str | None = None
    profile_status: str = "not_configured"
    last_refreshed_at: str | None = None
    last_error: str | None = None


class RebuildIndexResponse(BaseModel):
    """Response after rebuilding project embedding index."""

    indexed_count: int
    model_name: str


class BuildSourceEmbeddingsResponse(BaseModel):
    """Response after building embeddings for a source."""

    indexed_count: int
    source_id: str
    model_name: str


class RefreshKnowledgeIndexRequest(BaseModel):
    """Request body for refreshing knowledge index."""

    scope: KnowledgeRefreshScope = "project"
    source_id: str | None = None
    chunk_size: KnowledgeChunkSizeField = "medium"
    provider_id: str | None = None
    privacy_confirmed: bool = False


class RefreshKnowledgeIndexResponse(BaseModel):
    """Response after refreshing knowledge index."""

    source_count: int
    chunk_count: int
    indexed_count: int
    chunk_size: KnowledgeChunkSizeField
    model_name: str
    provider_id: str = ""
    warnings: list[str] = []


# --- Embedding Provider ---


class EmbeddingProviderInfo(BaseModel):
    """Describes a known embedding provider with availability status."""

    id: str
    display_name: str
    provider_type: EmbeddingProviderType
    model_name: str
    vector_dim: int
    available: bool
    reason: str = ""
    requires_privacy_confirm: bool = False
    requires_network: bool = False
    quality_label: str = ""
    description: str = ""


class EmbeddingProviderListResponse(BaseModel):
    """Response listing all known embedding providers."""

    providers: list[EmbeddingProviderInfo]
    default_provider_id: str


class IndexProfileResponse(BaseModel):
    """Current index profile for a project."""

    provider_id: str | None = None
    provider_type: str | None = None
    display_name: str | None = None
    model_name: str | None = None
    vector_dim: int | None = None
    chunk_size: str | None = None
    status: str | None = None
    last_refreshed_at: str | None = None
    last_error: str | None = None
