"""RAG (Retrieval-Augmented Generation) and AI Summary API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
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
from app.services.rag_service import (
    RagInvalidModeError,
    RagProjectNotFoundError,
    RagService,
)


router = APIRouter(tags=["knowledge-rag"])


def get_rag_service(db: Session = Depends(get_db)) -> RagService:
    return RagService(db)


def get_summary_service(db: Session = Depends(get_db)) -> AISummaryService:
    return AISummaryService(db)


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
    Currently uses stub LLM provider — answers are template placeholders.
    """
    try:
        return service.ask(
            project_id,
            request.question,
            mode=request.mode,
            source_type=request.source_type,
            credibility=request.credibility,
            top_k=request.top_k,
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
    Currently uses stub LLM provider — summaries are template placeholders.
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
