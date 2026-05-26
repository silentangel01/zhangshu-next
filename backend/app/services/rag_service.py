"""RAG (Retrieval-Augmented Generation) service for knowledge base Q&A."""

from sqlalchemy.orm import Session

from app.infrastructure.llm_provider import LLMProvider, StubLLMProvider
from app.repositories.project_repo import ProjectRepository
from app.schemas.rag import KnowledgeAskResponse, RagCitation
from app.services.retrieval_service import (
    RetrievalInvalidModeError,
    RetrievalProjectNotFoundError,
    RetrievalService,
)


# Fixed prompt when no relevant chunks are found
_INSUFFICIENT_CONTEXT_ANSWER = (
    "没有找到足够相关的知识库片段，建议补充相关资料或尝试切换匹配范围。"
)


class RagProjectNotFoundError(Exception):
    pass


class RagInvalidModeError(Exception):
    pass


class RagService:
    """RAG service: retrieve relevant chunks → generate answer with citations."""

    def __init__(
        self,
        db: Session,
        llm_provider: LLMProvider | None = None,
    ):
        self.db = db
        self.llm = llm_provider or StubLLMProvider()
        self.retrieval = RetrievalService(db)
        self.project_repo = ProjectRepository(db)

    def ask(
        self,
        project_id: str,
        question: str,
        *,
        mode: str = "hybrid",
        source_type: str | None = None,
        credibility: str | None = None,
        top_k: int = 10,
        strictness: str = "balanced",
    ) -> KnowledgeAskResponse:
        """Ask a question using RAG.

        1. Retrieve relevant chunks with quality filtering.
        2. If no high-quality results, return warning without calling LLM.
        3. Otherwise build context and generate answer.
        """
        self._ensure_project_exists(project_id)

        if not question.strip():
            return KnowledgeAskResponse(
                question=question,
                answer="",
                citations=[],
                model=self.llm.model_name,
                retrieval_mode=mode,
            )

        # 1. Retrieve relevant chunks with quality filtering
        try:
            retrieval_result = self.retrieval.search(
                project_id,
                question,
                mode=mode,
                source_type=source_type,
                credibility=credibility,
                limit=top_k,
                strictness=strictness,
            )
        except RetrievalProjectNotFoundError:
            raise RagProjectNotFoundError
        except RetrievalInvalidModeError as e:
            raise RagInvalidModeError(str(e))

        results = retrieval_result.results[:top_k]

        # 2. Check if we have enough relevant context
        if not results:
            return KnowledgeAskResponse(
                question=question,
                answer=_INSUFFICIENT_CONTEXT_ANSWER,
                citations=[],
                model=self.llm.model_name,
                retrieval_mode=mode,
                retrieval_warning=_INSUFFICIENT_CONTEXT_ANSWER,
            )

        # 3. Build context from chunk contents
        context = self._build_context(results)

        # 4. Generate answer via LLM
        answer = self.llm.generate(question, context)

        # 5. Build citations
        citations = [
            RagCitation(
                chunk_id=r.chunk_id,
                source_id=r.source_id,
                source_title=r.source_title,
                chunk_heading=r.chunk_heading,
                chunk_content=r.chunk_content,
                relevance_score=r.relevance_score,
                match_quality=r.match_quality,
            )
            for r in results
        ]

        # Build retrieval warning if many candidates were filtered
        retrieval_warning: str | None = None
        if retrieval_result.filtered_count > 0 and not results:
            retrieval_warning = _INSUFFICIENT_CONTEXT_ANSWER

        return KnowledgeAskResponse(
            question=question,
            answer=answer,
            citations=citations,
            model=self.llm.model_name,
            retrieval_mode=mode,
            retrieval_warning=retrieval_warning,
        )

    def _build_context(self, results: list) -> str:
        """Build context string from retrieval results."""
        if not results:
            return ""

        parts = []
        for r in results:
            header = f"[{r.source_title}]"
            if r.chunk_heading:
                header += f" {r.chunk_heading}"
            parts.append(f"{header}\n{r.chunk_content}")

        return "\n\n".join(parts)

    def _ensure_project_exists(self, project_id: str) -> None:
        project = self.project_repo.get_active(project_id)
        if project is None:
            raise RagProjectNotFoundError
