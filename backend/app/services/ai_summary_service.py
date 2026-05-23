"""AI Summary service for knowledge base content summarization."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.llm_provider import LLMProvider, StubLLMProvider
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_source import KnowledgeSource
from app.repositories.project_repo import ProjectRepository
from app.schemas.rag import KnowledgeSummaryResponse
from app.services.retrieval_service import (
    RetrievalInvalidModeError,
    RetrievalProjectNotFoundError,
    RetrievalService,
)


class SummaryProjectNotFoundError(Exception):
    pass


class SummaryInvalidModeError(Exception):
    pass


class AISummaryService:
    """AI Summary service: gather chunks → generate summary."""

    def __init__(
        self,
        db: Session,
        llm_provider: LLMProvider | None = None,
    ):
        self.db = db
        self.llm = llm_provider or StubLLMProvider()
        self.retrieval = RetrievalService(db)
        self.project_repo = ProjectRepository(db)

    def summarize(
        self,
        project_id: str,
        *,
        topic: str = "",
        source_ids: list[str] | None = None,
        mode: str = "hybrid",
    ) -> KnowledgeSummaryResponse:
        """Generate a summary of knowledge base content.

        If source_ids is provided, summarize chunks from those sources.
        Otherwise, use topic as a search query to find relevant chunks.

        The result is always marked as a draft (is_draft=True).
        """
        self._ensure_project_exists(project_id)

        # Gather chunks and source titles
        if source_ids:
            chunks, source_titles = self._gather_from_sources(source_ids)
        elif topic.strip():
            chunks, source_titles = self._gather_from_search(
                project_id, topic, mode
            )
        else:
            # No source_ids and no topic — summarize all active chunks
            chunks, source_titles = self._gather_all(project_id)

        # Extract text segments
        texts = [chunk.content for chunk in chunks if chunk.content.strip()]

        # Build instruction
        instruction = "总结以下知识库内容"
        if topic.strip():
            instruction += f"，聚焦主题：{topic}"

        # Generate summary
        summary = self.llm.summarize(texts, instruction)

        return KnowledgeSummaryResponse(
            summary=summary,
            sources_used=len(texts),
            source_titles=source_titles,
            model=self.llm.model_name,
            is_draft=True,
        )

    def _gather_from_sources(
        self, source_ids: list[str]
    ) -> tuple[list[KnowledgeChunk], list[str]]:
        """Gather chunks from specific sources."""
        stmt = (
            select(KnowledgeChunk, KnowledgeSource)
            .join(
                KnowledgeSource,
                KnowledgeChunk.source_id == KnowledgeSource.id,
            )
            .where(KnowledgeChunk.source_id.in_(source_ids))
            .where(KnowledgeChunk.deleted_at.is_(None))
            .where(KnowledgeSource.deleted_at.is_(None))
            .order_by(
                KnowledgeSource.title,
                KnowledgeChunk.chunk_index,
            )
        )
        rows = self.db.execute(stmt).all()

        chunks = [chunk for chunk, _ in rows]
        source_titles = list({source.title for _, source in rows})

        return chunks, source_titles

    def _gather_from_search(
        self, project_id: str, topic: str, mode: str
    ) -> tuple[list[KnowledgeChunk], list[str]]:
        """Gather chunks by searching for a topic."""
        try:
            result = self.retrieval.search(
                project_id, topic, mode=mode, limit=20
            )
        except RetrievalProjectNotFoundError:
            raise SummaryProjectNotFoundError
        except RetrievalInvalidModeError as e:
            raise SummaryInvalidModeError(str(e))

        # Load full chunks from retrieval results
        chunk_ids = [r.chunk_id for r in result.results]
        if not chunk_ids:
            return [], []

        stmt = (
            select(KnowledgeChunk, KnowledgeSource)
            .join(
                KnowledgeSource,
                KnowledgeChunk.source_id == KnowledgeSource.id,
            )
            .where(KnowledgeChunk.id.in_(chunk_ids))
        )
        rows = self.db.execute(stmt).all()

        # Preserve retrieval order
        chunk_map = {chunk.id: (chunk, source) for chunk, source in rows}
        chunks = []
        source_titles = set()
        for cid in chunk_ids:
            if cid in chunk_map:
                chunk, source = chunk_map[cid]
                chunks.append(chunk)
                source_titles.add(source.title)

        return chunks, list(source_titles)

    def _gather_all(
        self, project_id: str
    ) -> tuple[list[KnowledgeChunk], list[str]]:
        """Gather all active chunks in a project."""
        stmt = (
            select(KnowledgeChunk, KnowledgeSource)
            .join(
                KnowledgeSource,
                KnowledgeChunk.source_id == KnowledgeSource.id,
            )
            .where(KnowledgeChunk.project_id == project_id)
            .where(KnowledgeChunk.deleted_at.is_(None))
            .where(KnowledgeSource.deleted_at.is_(None))
            .order_by(
                KnowledgeSource.title,
                KnowledgeChunk.chunk_index,
            )
            .limit(50)
        )
        rows = self.db.execute(stmt).all()

        chunks = [chunk for chunk, _ in rows]
        source_titles = list({source.title for _, source in rows})

        return chunks, source_titles

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise SummaryProjectNotFoundError
