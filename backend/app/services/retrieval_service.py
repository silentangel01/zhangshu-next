"""Unified retrieval service combining keyword and semantic search."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.embedding_provider import (
    BigramHashEmbeddingProvider,
    EmbeddingProvider,
)
from app.infrastructure.vector_store import SqliteVectorStore, VectorStore
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_source import KnowledgeSource
from app.repositories.project_repo import ProjectRepository
from app.schemas.knowledge_retrieval import (
    KnowledgeRetrievalChunkResult,
    KnowledgeRetrievalResponse,
)
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService


VALID_MODES = ("keyword", "semantic", "hybrid")


class RetrievalProjectNotFoundError(Exception):
    pass


class RetrievalInvalidModeError(Exception):
    pass


class RetrievalService:
    """Unified retrieval service supporting keyword, semantic, and hybrid modes."""

    def __init__(
        self,
        db: Session,
        provider: EmbeddingProvider | None = None,
        store: VectorStore | None = None,
    ):
        self.db = db
        self.provider = provider or BigramHashEmbeddingProvider()
        self.store = store or SqliteVectorStore(db)
        self.keyword_service = KnowledgeRetrievalService(db)
        self.project_repo = ProjectRepository(db)

    def search(
        self,
        project_id: str,
        query: str,
        *,
        mode: str = "keyword",
        source_type: str | None = None,
        credibility: str | None = None,
        tag: str | None = None,
        source_id: str | None = None,
        limit: int = 50,
    ) -> KnowledgeRetrievalResponse:
        """Search knowledge chunks using the specified mode.

        Args:
            project_id: Project to search within.
            query: Search query text.
            mode: Search mode - "keyword", "semantic", or "hybrid".
            source_type: Optional source type filter.
            credibility: Optional credibility filter.
            tag: Optional tag filter.
            source_id: Optional source ID filter.
            limit: Maximum results to return.

        Returns:
            KnowledgeRetrievalResponse with results and mode.
        """
        if mode not in VALID_MODES:
            raise RetrievalInvalidModeError(
                f"Invalid mode '{mode}'. Must be one of: {', '.join(VALID_MODES)}"
            )

        self._ensure_project_exists(project_id)

        if not query.strip():
            return KnowledgeRetrievalResponse(
                keyword=query, total=0, results=[], mode=mode
            )

        if mode == "keyword":
            return self._search_keyword(
                project_id,
                query,
                source_type=source_type,
                credibility=credibility,
                tag=tag,
                source_id=source_id,
                limit=limit,
            )
        elif mode == "semantic":
            return self._search_semantic(
                project_id,
                query,
                source_type=source_type,
                credibility=credibility,
                tag=tag,
                source_id=source_id,
                limit=limit,
            )
        else:  # hybrid
            return self._search_hybrid(
                project_id,
                query,
                source_type=source_type,
                credibility=credibility,
                tag=tag,
                source_id=source_id,
                limit=limit,
            )

    def _search_keyword(
        self,
        project_id: str,
        query: str,
        *,
        source_type: str | None = None,
        credibility: str | None = None,
        tag: str | None = None,
        source_id: str | None = None,
        limit: int = 50,
    ) -> KnowledgeRetrievalResponse:
        """Delegate to existing keyword search service."""
        result = self.keyword_service.search_chunks(
            project_id,
            query,
            source_type=source_type,
            credibility=credibility,
            tag=tag,
            source_id=source_id,
            limit=limit,
        )
        result.mode = "keyword"
        return result

    def _search_semantic(
        self,
        project_id: str,
        query: str,
        *,
        source_type: str | None = None,
        credibility: str | None = None,
        tag: str | None = None,
        source_id: str | None = None,
        limit: int = 50,
    ) -> KnowledgeRetrievalResponse:
        """Search using vector similarity."""
        # Encode query
        query_vector = self.provider.encode(query)

        # Build filters dict
        filters: dict = {}
        if source_type:
            filters["source_type"] = source_type
        if credibility:
            filters["credibility"] = credibility
        if tag:
            filters["tag"] = tag
        if source_id:
            filters["source_id"] = source_id

        # Vector search
        vector_results = self.store.search(
            query_vector=query_vector,
            project_id=project_id,
            filters=filters if filters else None,
            top_k=limit,
        )

        if not vector_results:
            return KnowledgeRetrievalResponse(
                keyword=query, total=0, results=[], mode="semantic"
            )

        # Load chunk details for results
        chunk_ids = [r.chunk_id for r in vector_results]
        score_map = {r.chunk_id: r.score for r in vector_results}

        stmt = (
            select(KnowledgeChunk, KnowledgeSource)
            .join(
                KnowledgeSource,
                KnowledgeChunk.source_id == KnowledgeSource.id,
            )
            .where(KnowledgeChunk.id.in_(chunk_ids))
        )
        rows = self.db.execute(stmt).all()

        # Build result list preserving vector search order
        chunk_map = {chunk.id: (chunk, source) for chunk, source in rows}
        results = []
        for vr in vector_results:
            if vr.chunk_id in chunk_map:
                chunk, source = chunk_map[vr.chunk_id]
                # For semantic search, use first 100 chars as snippet
                snippet = chunk.content[:100] if chunk.content else ""
                context_after = chunk.content[100:200] if len(chunk.content) > 100 else ""
                results.append(
                    KnowledgeRetrievalChunkResult(
                        chunk_id=chunk.id,
                        chunk_index=chunk.chunk_index,
                        chunk_heading=chunk.heading,
                        chunk_content=chunk.content,
                        matched_snippet=snippet,
                        context_before="",
                        context_after=context_after,
                        source_id=source.id,
                        source_title=source.title,
                        source_type=source.source_type,
                        source_credibility=source.credibility,
                        relevance_score=score_map[vr.chunk_id],
                    )
                )

        return KnowledgeRetrievalResponse(
            keyword=query, total=len(results), results=results, mode="semantic"
        )

    def _search_hybrid(
        self,
        project_id: str,
        query: str,
        *,
        source_type: str | None = None,
        credibility: str | None = None,
        tag: str | None = None,
        source_id: str | None = None,
        limit: int = 50,
    ) -> KnowledgeRetrievalResponse:
        """Combine keyword and semantic search results."""
        # Run both searches
        keyword_result = self._search_keyword(
            project_id,
            query,
            source_type=source_type,
            credibility=credibility,
            tag=tag,
            source_id=source_id,
            limit=limit,
        )
        semantic_result = self._search_semantic(
            project_id,
            query,
            source_type=source_type,
            credibility=credibility,
            tag=tag,
            source_id=source_id,
            limit=limit,
        )

        # Merge and deduplicate (keyword results take priority)
        seen_chunk_ids: set[str] = set()
        merged_results: list[KnowledgeRetrievalChunkResult] = []

        for r in keyword_result.results:
            if r.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(r.chunk_id)
                merged_results.append(r)

        for r in semantic_result.results:
            if r.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(r.chunk_id)
                merged_results.append(r)

        # Apply limit
        merged_results = merged_results[:limit]

        return KnowledgeRetrievalResponse(
            keyword=query,
            total=len(merged_results),
            results=merged_results,
            mode="hybrid",
        )

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise RetrievalProjectNotFoundError
