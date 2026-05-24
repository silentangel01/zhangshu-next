from pydantic import BaseModel, ConfigDict


class KnowledgeRetrievalRequest(BaseModel):
    """Chunk-level search request."""
    keyword: str
    source_type: str | None = None
    credibility: str | None = None
    tag: str | None = None
    source_id: str | None = None
    limit: int = 20
    mode: str = "keyword"
    strictness: str = "balanced"


class KnowledgeRetrievalChunkResult(BaseModel):
    """Single chunk match with source context and quality info."""
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
    # Quality layer fields (all optional for backward compat)
    vector_score: float | None = None
    keyword_score: float | None = None
    final_score: float | None = None
    match_quality: str | None = None
    match_reason: str | None = None


class KnowledgeRetrievalResponse(BaseModel):
    """Chunk search response with quality diagnostics."""
    keyword: str
    total: int
    results: list[KnowledgeRetrievalChunkResult]
    mode: str = "keyword"
    strictness: str = "balanced"
    candidate_count: int = 0
    filtered_count: int = 0
    warnings: list[str] = []
