from pydantic import BaseModel


class IndexStatusResponse(BaseModel):
    """Embedding index status for a project."""

    total_chunks: int
    indexed_chunks: int
    unindexed_chunks: int
    model_name: str


class RebuildIndexResponse(BaseModel):
    """Response after rebuilding project embedding index."""

    indexed_count: int
    model_name: str


class BuildSourceEmbeddingsResponse(BaseModel):
    """Response after building embeddings for a source."""

    indexed_count: int
    source_id: str
    model_name: str
