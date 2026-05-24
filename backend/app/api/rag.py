"""RAG (Retrieval-Augmented Generation) and AI Summary API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.llm_provider import LLMProvider
from app.infrastructure.llm_provider_factory import LLMProviderFactory
from app.schemas.rag import (
    KnowledgeAskRequest,
    KnowledgeAskResponse,
    KnowledgeSummaryRequest,
    KnowledgeSummaryResponse,
)
from app.services.ai_summary_service import (
    AISummaryService,
    SummaryInvalidModeError,
    SummaryProjectNotFoundError,
)
from app.services.app_config_service import AppConfigService
from app.services.rag_service import (
    RagInvalidModeError,
    RagProjectNotFoundError,
    RagService,
)


router = APIRouter(tags=["knowledge-rag"])


def get_llm_provider(db: Session = Depends(get_db)) -> LLMProvider:
    """Create LLM provider based on app config (stub or DashScope)."""
    config_service = AppConfigService(db)
    factory = LLMProviderFactory(config_service)
    return factory.create()


def get_rag_service(
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> RagService:
    return RagService(db, llm_provider=llm)


def get_summary_service(
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> AISummaryService:
    return AISummaryService(db, llm_provider=llm)


@router.post(
    "/api/projects/{project_id}/knowledge/ask",
    response_model=KnowledgeAskResponse,
)
def ask_knowledge_base(
    project_id: str,
    request: KnowledgeAskRequest,
    service: RagService = Depends(get_rag_service),
) -> KnowledgeAskResponse:
    """Ask a question using RAG (Retrieval-Augmented Generation).

    Retrieves relevant knowledge chunks and generates an answer with citations.
    Uses stub LLM when cloud LLM is not configured, DashScope when enabled.
    """
    try:
        return service.ask(
            project_id,
            request.question,
            mode=request.mode,
            source_type=request.source_type,
            credibility=request.credibility,
            top_k=request.top_k,
            strictness=request.strictness,
        )
    except RagProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except RagInvalidModeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/projects/{project_id}/knowledge/summary",
    response_model=KnowledgeSummaryResponse,
)
def summarize_knowledge(
    project_id: str,
    request: KnowledgeSummaryRequest,
    service: AISummaryService = Depends(get_summary_service),
) -> KnowledgeSummaryResponse:
    """Generate an AI summary of knowledge base content.

    Can summarize specific sources or search by topic.
    Result is always marked as a draft (is_draft=true).
    Uses stub LLM when cloud LLM is not configured, DashScope when enabled.
    """
    try:
        return service.summarize(
            project_id,
            topic=request.topic,
            source_ids=request.source_ids,
            mode=request.mode,
        )
    except SummaryProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except SummaryInvalidModeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
