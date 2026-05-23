from pydantic import BaseModel, ConfigDict


class KnowledgeRetrievalRequest(BaseModel):
    """Chunk-level search request."""
    keyword: str
    source_type: str | None = None
    credibility: str | None = None
    tag: str | None = None
    source_id: str | None = None
    limit: int = 50
    mode: str = "keyword"


class KnowledgeRetrievalChunkResult(BaseModel):
    """Single chunk match with source context."""
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    chunk_index: int
    chunk_heading: str
    chunk_content: str
    matched_snippet: str
    context_before: str
    context_after: str
    source_id: str
    source_title: str
    source_type: str
    source_credibility: str
    relevance_score: float | None = None


class KnowledgeRetrievalResponse(BaseModel):
    """Chunk search response."""
    keyword: str
    total: int
    results: list[KnowledgeRetrievalChunkResult]
    mode: str = "keyword"
