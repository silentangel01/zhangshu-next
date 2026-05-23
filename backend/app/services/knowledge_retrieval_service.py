from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_source import KnowledgeSource
from app.repositories.project_repo import ProjectRepository
from app.schemas.knowledge_retrieval import (
    KnowledgeRetrievalChunkResult,
    KnowledgeRetrievalResponse,
)


SNIPPET_CONTEXT_CHARS = 80


class KnowledgeRetrievalProjectNotFoundError(Exception):
    pass


class KnowledgeRetrievalService:
    """Chunk-level search with context extraction and citation info."""

    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)

    def search_chunks(
        self,
        project_id: str,
        keyword: str,
        *,
        source_type: str | None = None,
        credibility: str | None = None,
        tag: str | None = None,
        source_id: str | None = None,
        limit: int = 50,
    ) -> KnowledgeRetrievalResponse:
        """Search knowledge chunks by keyword with context extraction."""
        self._ensure_project_exists(project_id)

        if not keyword.strip():
            return KnowledgeRetrievalResponse(keyword=keyword, total=0, results=[])

        # Build chunk query
        statement = (
            select(KnowledgeChunk, KnowledgeSource)
            .join(
                KnowledgeSource,
                KnowledgeChunk.source_id == KnowledgeSource.id,
            )
            .where(
                KnowledgeChunk.project_id == project_id,
                KnowledgeChunk.deleted_at.is_(None),
                KnowledgeSource.deleted_at.is_(None),
            )
        )

        # Keyword search across chunk content and heading
        pattern = f"%{keyword.strip()}%"
        statement = statement.where(
            KnowledgeChunk.content.ilike(pattern)
            | KnowledgeChunk.heading.ilike(pattern)
        )

        # Apply filters
        if source_type:
            statement = statement.where(KnowledgeSource.source_type == source_type)
        if credibility:
            statement = statement.where(KnowledgeSource.credibility == credibility)
        if tag:
            tag_pattern = f"%{tag}%"
            statement = statement.where(KnowledgeSource.tags.ilike(tag_pattern))
        if source_id:
            statement = statement.where(KnowledgeChunk.source_id == source_id)

        # Order by relevance (chunk index) and limit
        statement = statement.order_by(
            KnowledgeSource.updated_at.desc(),
            KnowledgeChunk.chunk_index.asc(),
        ).limit(limit)

        rows = self.db.execute(statement).all()

        results = []
        for chunk, source in rows:
            matched_snippet, context_before, context_after = self._extract_context(
                chunk.content, keyword.strip()
            )
            results.append(
                KnowledgeRetrievalChunkResult(
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    chunk_heading=chunk.heading,
                    chunk_content=chunk.content,
                    matched_snippet=matched_snippet,
                    context_before=context_before,
                    context_after=context_after,
                    source_id=source.id,
                    source_title=source.title,
                    source_type=source.source_type,
                    source_credibility=source.credibility,
                )
            )

        return KnowledgeRetrievalResponse(
            keyword=keyword, total=len(results), results=results
        )

    def _extract_context(
        self, content: str, keyword: str
    ) -> tuple[str, str, str]:
        """Extract matched snippet with surrounding context.

        Returns: (matched_snippet, context_before, context_after)
        """
        keyword_lower = keyword.lower()
        content_lower = content.lower()
        match_pos = content_lower.find(keyword_lower)

        if match_pos < 0:
            # Keyword not found in content (might be in heading)
            # Return first part of content as snippet
            snippet = content[:SNIPPET_CONTEXT_CHARS * 2]
            return (snippet, "", content[SNIPPET_CONTEXT_CHARS * 2 :] if len(content) > SNIPPET_CONTEXT_CHARS * 2 else "")

        # Calculate context boundaries
        start = max(0, match_pos - SNIPPET_CONTEXT_CHARS)
        end = min(len(content), match_pos + len(keyword) + SNIPPET_CONTEXT_CHARS)

        context_before = content[start:match_pos]
        matched_snippet = content[match_pos : match_pos + len(keyword)]
        context_after = content[match_pos + len(keyword) : end]

        # Extend to word boundaries if possible
        if start > 0:
            # Find last space/newline before start
            space_pos = content.rfind(" ", 0, start)
            if space_pos >= 0 and start - space_pos < 20:
                context_before = content[space_pos + 1 : match_pos]

        if end < len(content):
            # Find next space/newline after end
            space_pos = content.find(" ", end)
            if space_pos >= 0 and space_pos - end < 20:
                context_after = content[match_pos + len(keyword) : space_pos]

        return (matched_snippet, context_before, context_after)

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise KnowledgeRetrievalProjectNotFoundError
