"""Schemas for RAG (Retrieval-Augmented Generation) endpoints."""

from pydantic import BaseModel


class KnowledgeAskRequest(BaseModel):
    """Request for RAG question answering."""

    question: str
    mode: str = "hybrid"
    source_type: str | None = None
    credibility: str | None = None
    top_k: int = 10
    strictness: str = "balanced"


class RagCitation(BaseModel):
    """Citation for a RAG response, referencing a knowledge chunk."""

    chunk_id: str
    source_id: str
    source_title: str
    chunk_heading: str
    chunk_content: str
    relevance_score: float | None = None
    match_quality: str | None = None


class KnowledgeAskResponse(BaseModel):
    """RAG response with answer and citations."""

    question: str
    answer: str
    citations: list[RagCitation]
    model: str
    retrieval_mode: str
    retrieval_warning: str | None = None


class KnowledgeSummaryRequest(BaseModel):
    """Request for AI-powered knowledge summary."""

    topic: str = ""
    source_ids: list[str] | None = None
    mode: str = "hybrid"


class KnowledgeSummaryResponse(BaseModel):
    """AI summary response with source attribution."""

    summary: str
    sources_used: int
    source_titles: list[str]
    model: str
    is_draft: bool = True
    warnings: list[str] = []
