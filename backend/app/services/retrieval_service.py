"""Unified retrieval service combining keyword and semantic search."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.embedding_provider import (
    BigramHashEmbeddingProvider,
    EmbeddingProvider,
)
from app.infrastructure.embedding_provider_factory import (
    create_provider,
    get_default_provider,
)
from app.infrastructure.vector_store import SqliteVectorStore, VectorStore
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_source import KnowledgeSource
from app.repositories.knowledge_index_profile_repo import KnowledgeIndexProfileRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.knowledge_retrieval import (
    KnowledgeRetrievalChunkResult,
    KnowledgeRetrievalResponse,
)
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService
from app.services.retrieval_quality_service import (
    QualityEvaluation,
    RetrievalCandidate,
    RetrievalQualityService,
    RetrievalStrictness,
)


VALID_MODES = ("keyword", "semantic", "hybrid")

# Candidate over-fetch multiplier for quality filtering
_CANDIDATE_FACTOR = 4
_CANDIDATE_MIN = 40
_CANDIDATE_MAX = 120


def _candidate_limit(limit: int) -> int:
    return min(max(limit * _CANDIDATE_FACTOR, _CANDIDATE_MIN), _CANDIDATE_MAX)


def _parse_tags(raw: str) -> list[str]:
    """Parse comma-separated tags string into a list."""
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


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
        quality_service: RetrievalQualityService | None = None,
    ):
        self.db = db
        self.provider = provider or BigramHashEmbeddingProvider()
        self.store = store or SqliteVectorStore(db)
        self.keyword_service = KnowledgeRetrievalService(db)
        self.project_repo = ProjectRepository(db)
        self.profile_repo = KnowledgeIndexProfileRepository(db)
        self.quality_service = quality_service or RetrievalQualityService()
        self._explicit_provider = provider is not None

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
        limit: int = 20,
        strictness: RetrievalStrictness = "balanced",
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
            strictness: Matching strictness for quality filtering.

        Returns:
            KnowledgeRetrievalResponse with results and diagnostics.
        """
        if mode not in VALID_MODES:
            raise RetrievalInvalidModeError(
                f"Invalid mode '{mode}'. Must be one of: {', '.join(VALID_MODES)}"
            )

        self._ensure_project_exists(project_id)

        if not query.strip():
            return KnowledgeRetrievalResponse(
                keyword=query, total=0, results=[], mode=mode,
                strictness=strictness, candidate_count=0,
                filtered_count=0, warnings=[],
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
                strictness=strictness,
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
                strictness=strictness,
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
                strictness=strictness,
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
        limit: int = 20,
        strictness: RetrievalStrictness = "balanced",
    ) -> KnowledgeRetrievalResponse:
        """Keyword search with quality filtering."""
        # Over-fetch candidates from keyword service
        candidate_count = _candidate_limit(limit)
        kw_response = self.keyword_service.search_chunks(
            project_id,
            query,
            source_type=source_type,
            credibility=credibility,
            tag=tag,
            source_id=source_id,
            limit=candidate_count,
        )

        if not kw_response.results:
            return KnowledgeRetrievalResponse(
                keyword=query, total=0, results=[], mode="keyword",
                strictness=strictness, candidate_count=0,
                filtered_count=0, warnings=[],
            )

        # Build candidates from keyword results
        candidates = self._build_keyword_candidates(kw_response.results)

        # Quality evaluation
        evaluation = self.quality_service.evaluate_candidates(
            query=query,
            candidates=candidates,
            strictness=strictness,
            mode="keyword",
            provider_model_name=None,
            limit=limit,
        )

        return self._build_response(
            query, evaluation, mode="keyword", strictness=strictness,
        )

    def _search_semantic(
        self,
        project_id: str,
        query: str,
        *,
        source_type: str | None = None,
        credibility: str | None = None,
        tag: str | None = None,
        source_id: str | None = None,
        limit: int = 20,
        strictness: RetrievalStrictness = "balanced",
    ) -> KnowledgeRetrievalResponse:
        """Search using vector similarity with quality filtering."""
        # Resolve provider from project profile
        query_provider = self._resolve_query_provider(project_id)

        # Encode query using resolved provider
        query_vector = query_provider.encode(query)

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

        # Over-fetch candidates for quality filtering
        candidate_count = _candidate_limit(limit)
        vector_results = self.store.search(
            query_vector=query_vector,
            project_id=project_id,
            filters=filters if filters else None,
            top_k=candidate_count,
            model_name=query_provider.model_name,
            vector_dim=query_provider.vector_dim,
        )

        if not vector_results:
            return KnowledgeRetrievalResponse(
                keyword=query, total=0, results=[], mode="semantic",
                strictness=strictness, candidate_count=0,
                filtered_count=0, warnings=[],
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

        # Build candidates
        chunk_map = {chunk.id: (chunk, source) for chunk, source in rows}
        candidates: list[RetrievalCandidate] = []
        for vr in vector_results:
            if vr.chunk_id in chunk_map:
                chunk, source = chunk_map[vr.chunk_id]
                candidates.append(
                    RetrievalCandidate(
                        chunk_id=chunk.id,
                        source_id=source.id,
                        chunk_heading=chunk.heading,
                        chunk_content=chunk.content,
                        chunk_index=chunk.chunk_index,
                        source_title=source.title,
                        source_type=source.source_type,
                        source_credibility=source.credibility,
                        source_tags=_parse_tags(source.tags),
                        vector_score=score_map[vr.chunk_id],
                    )
                )

        # Quality evaluation
        evaluation = self.quality_service.evaluate_candidates(
            query=query,
            candidates=candidates,
            strictness=strictness,
            mode="semantic",
            provider_model_name=query_provider.model_name,
            limit=limit,
        )

        return self._build_response(
            query, evaluation, mode="semantic", strictness=strictness,
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
        limit: int = 20,
        strictness: RetrievalStrictness = "balanced",
    ) -> KnowledgeRetrievalResponse:
        """Combine keyword and semantic search with unified quality scoring."""
        candidate_count = _candidate_limit(limit)

        # --- Keyword candidates ---
        kw_response = self.keyword_service.search_chunks(
            project_id,
            query,
            source_type=source_type,
            credibility=credibility,
            tag=tag,
            source_id=source_id,
            limit=candidate_count,
        )
        kw_candidates = self._build_keyword_candidates(kw_response.results)

        # --- Semantic candidates ---
        query_provider = self._resolve_query_provider(project_id)
        query_vector = query_provider.encode(query)

        filters: dict = {}
        if source_type:
            filters["source_type"] = source_type
        if credibility:
            filters["credibility"] = credibility
        if tag:
            filters["tag"] = tag
        if source_id:
            filters["source_id"] = source_id

        vector_results = self.store.search(
            query_vector=query_vector,
            project_id=project_id,
            filters=filters if filters else None,
            top_k=candidate_count,
            model_name=query_provider.model_name,
            vector_dim=query_provider.vector_dim,
        )

        sem_candidates: list[RetrievalCandidate] = []
        if vector_results:
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
            chunk_map = {chunk.id: (chunk, source) for chunk, source in rows}

            for vr in vector_results:
                if vr.chunk_id in chunk_map:
                    chunk, source = chunk_map[vr.chunk_id]
                    sem_candidates.append(
                        RetrievalCandidate(
                            chunk_id=chunk.id,
                            source_id=source.id,
                            chunk_heading=chunk.heading,
                            chunk_content=chunk.content,
                            chunk_index=chunk.chunk_index,
                            source_title=source.title,
                            source_type=source.source_type,
                            source_credibility=source.credibility,
                            source_tags=_parse_tags(source.tags),
                            vector_score=score_map[vr.chunk_id],
                        )
                    )

        # --- Merge candidates by chunk_id ---
        merged = self._merge_candidates(kw_candidates, sem_candidates)

        total_candidates = len(kw_candidates) + len(sem_candidates)

        # --- Quality evaluation ---
        evaluation = self.quality_service.evaluate_candidates(
            query=query,
            candidates=merged,
            strictness=strictness,
            mode="hybrid",
            provider_model_name=query_provider.model_name,
            limit=limit,
        )

        # Adjust candidate_count to reflect original (pre-dedup) count
        evaluation.candidate_count = total_candidates

        return self._build_response(
            query, evaluation, mode="hybrid", strictness=strictness,
        )

    # -- Helpers --

    def _build_keyword_candidates(
        self, results: list[KnowledgeRetrievalChunkResult]
    ) -> list[RetrievalCandidate]:
        """Convert keyword search results into RetrievalCandidate objects."""
        candidates: list[RetrievalCandidate] = []
        for r in results:
            candidates.append(
                RetrievalCandidate(
                    chunk_id=r.chunk_id,
                    source_id=r.source_id,
                    chunk_heading=r.chunk_heading,
                    chunk_content=r.chunk_content,
                    chunk_index=r.chunk_index,
                    source_title=r.source_title,
                    source_type=r.source_type,
                    source_credibility=r.source_credibility,
                    source_tags=_parse_tags(
                        # tags not on the result schema; leave empty
                        ""
                    ),
                    keyword_score=1.0,  # keyword matched — base score
                )
            )
        return candidates

    @staticmethod
    def _merge_candidates(
        kw: list[RetrievalCandidate],
        sem: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        """Merge keyword and semantic candidates by chunk_id.

        When the same chunk appears in both lists, combine scores:
        keep max(vector_score) and max(keyword_score).
        """
        by_id: dict[str, RetrievalCandidate] = {}

        for c in kw:
            by_id[c.chunk_id] = c

        for c in sem:
            existing = by_id.get(c.chunk_id)
            if existing is not None:
                # Merge scores
                existing.vector_score = max(
                    existing.vector_score or 0.0, c.vector_score or 0.0
                )
                existing.keyword_score = max(
                    existing.keyword_score or 0.0, c.keyword_score or 0.0
                )
            else:
                by_id[c.chunk_id] = c

        return list(by_id.values())

    def _build_response(
        self,
        query: str,
        evaluation: QualityEvaluation,
        *,
        mode: str,
        strictness: RetrievalStrictness,
    ) -> KnowledgeRetrievalResponse:
        """Build KnowledgeRetrievalResponse from quality evaluation."""
        results: list[KnowledgeRetrievalChunkResult] = []

        for qr in evaluation.results:
            c = qr.candidate
            # Extract snippet around first anchor hit in content
            snippet, ctx_before, ctx_after = self._extract_snippet(
                c.chunk_content, query,
            )
            results.append(
                KnowledgeRetrievalChunkResult(
                    chunk_id=c.chunk_id,
                    chunk_index=c.chunk_index,
                    chunk_heading=c.chunk_heading,
                    chunk_content=c.chunk_content,
                    matched_snippet=snippet,
                    context_before=ctx_before,
                    context_after=ctx_after,
                    source_id=c.source_id,
                    source_title=c.source_title,
                    source_type=c.source_type,
                    source_credibility=c.source_credibility,
                    relevance_score=qr.final_score,
                    vector_score=qr.vector_score_norm,
                    keyword_score=qr.keyword_score_norm,
                    final_score=qr.final_score,
                    match_quality=qr.match_quality,
                    match_reason=qr.match_reason,
                )
            )

        return KnowledgeRetrievalResponse(
            keyword=query,
            total=len(results),
            results=results,
            mode=mode,
            strictness=strictness,
            candidate_count=evaluation.candidate_count,
            filtered_count=evaluation.filtered_count,
            warnings=evaluation.warnings,
        )

    @staticmethod
    def _extract_snippet(
        content: str, query: str
    ) -> tuple[str, str, str]:
        """Extract snippet around first query anchor hit in content.

        Falls back to first 100 chars if no anchor found in content.
        Returns: (matched_snippet, context_before, context_after)
        """
        if not content:
            return ("", "", "")

        query_lower = query.lower().strip()
        content_lower = content.lower()

        # Try to find query (or a significant part) in content
        match_pos = content_lower.find(query_lower)
        if match_pos < 0 and len(query_lower) > 2:
            # Try first 4+ chars as anchor
            anchor = query_lower[:4] if len(query_lower) >= 4 else query_lower
            match_pos = content_lower.find(anchor)

        if match_pos < 0:
            # Fallback: first 100 chars
            snippet = content[:100]
            ctx_after = content[100:200] if len(content) > 100 else ""
            return (snippet, "", ctx_after)

        # Extract ±80 chars around match
        ctx_chars = 80
        start = max(0, match_pos - ctx_chars)
        end = min(len(content), match_pos + len(query_lower) + ctx_chars)

        ctx_before = content[start:match_pos]
        matched = content[match_pos : match_pos + len(query_lower)]
        ctx_after = content[match_pos + len(query_lower) : end]

        return (matched, ctx_before, ctx_after)

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise RetrievalProjectNotFoundError

    def _resolve_query_provider(self, project_id: str) -> EmbeddingProvider:
        """Resolve the embedding provider for query encoding."""
        if self._explicit_provider:
            return self.provider

        profile = self.profile_repo.get_by_project(project_id)
        if profile is None:
            return self.provider  # default

        return create_provider(profile.provider_id)
