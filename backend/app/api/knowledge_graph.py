import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal, get_db
from app.infrastructure.llm_provider import LLMProvider
from app.infrastructure.llm_provider_factory import LLMProviderFactory
from app.schemas.knowledge_graph import (
    KnowledgeGraphEntityList,
    KnowledgeGraphEntityRead,
    KnowledgeGraphExtractionRunCreate,
    KnowledgeGraphExtractionRunRead,
    KnowledgeGraphFactStatus,
    KnowledgeGraphRelationList,
    KnowledgeGraphRelationRead,
    KnowledgeGraphRelationType,
    KnowledgeGraphRunList,
    KnowledgeGraphStatus,
    KnowledgeGraphSubgraph,
)
from app.services.app_config_service import AppConfigService
from app.services.knowledge_graph_extraction_service import (
    KnowledgeGraphExtractionChunkLimitError,
    KnowledgeGraphExtractionError,
    KnowledgeGraphExtractionMissingSourceError,
    KnowledgeGraphExtractionPrivacyNotConfirmedError,
    KnowledgeGraphExtractionProjectNotFoundError,
    KnowledgeGraphExtractionService,
    KnowledgeGraphExtractionSourceNotFoundError,
)
from app.services.knowledge_graph_service import (
    KnowledgeGraphEntityNotFoundError,
    KnowledgeGraphProjectNotFoundError,
    KnowledgeGraphRelationNotFoundError,
    KnowledgeGraphService,
)


router = APIRouter(tags=["knowledge-graph"])
logger = logging.getLogger(__name__)


def _error_detail(message: str, error_kind: str, suggestion: str | None = None) -> dict:
    detail = {"message": message, "error_kind": error_kind}
    if suggestion:
        detail["suggestion"] = suggestion
    return detail


def get_knowledge_graph_service(db: Session = Depends(get_db)) -> KnowledgeGraphService:
    return KnowledgeGraphService(db)


def get_configured_llm_provider(db: Session = Depends(get_db)) -> LLMProvider:
    config_service = AppConfigService(db)
    factory = LLMProviderFactory(config_service)
    if not factory.is_cloud_llm_enabled():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_error_detail(
                "尚未配置可用的 AI 模型。",
                "llm_not_configured",
                "请在应用设置中填写用户自己的 API Key，并启用 AI 问答模型后再抽取知识图谱。",
            ),
        )
    return factory.create()


def get_knowledge_graph_extraction_service(
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_configured_llm_provider),
) -> KnowledgeGraphExtractionService:
    return KnowledgeGraphExtractionService(db, llm)


def _process_knowledge_graph_extraction_run(run_id: str) -> None:
    db = SessionLocal()
    try:
        config_service = AppConfigService(db)
        factory = LLMProviderFactory(config_service)
        service = KnowledgeGraphExtractionService(db, factory.create())
        if not factory.is_cloud_llm_enabled():
            service.mark_run_failed(
                run_id,
                "AI 模型配置已失效，请重新配置用户 API Key 并启用 AI 能力。",
            )
            return
        service.process_run(run_id)
    except Exception:
        logger.exception("Knowledge graph extraction background run failed: %s", run_id)
    finally:
        db.close()


@router.post(
    "/api/projects/{project_id}/knowledge-graph/extraction-runs",
    response_model=KnowledgeGraphExtractionRunRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_graph_extraction_run(
    project_id: str,
    request: KnowledgeGraphExtractionRunCreate,
    background_tasks: BackgroundTasks,
    service: KnowledgeGraphExtractionService = Depends(
        get_knowledge_graph_extraction_service
    ),
):
    try:
        run = service.create_pending_run(project_id, request)
        background_tasks.add_task(_process_knowledge_graph_extraction_run, run.id)
        return run
    except KnowledgeGraphExtractionProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except (
        KnowledgeGraphExtractionSourceNotFoundError,
        KnowledgeGraphExtractionMissingSourceError,
    ) as exc:
        raise HTTPException(status_code=404, detail="Knowledge source not found") from exc
    except KnowledgeGraphExtractionPrivacyNotConfirmedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_error_detail(
                "需要先确认发送资料片段到外部 AI 服务。",
                "privacy_not_confirmed",
                "勾选确认后再开始抽取；若不希望发送资料内容，可以继续只使用本地知识库。",
            ),
        ) from exc
    except KnowledgeGraphExtractionChunkLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_error_detail(
                f"本次范围包含 {exc.chunk_count} 个片段，超过上限 {exc.max_chunks}。",
                "chunk_limit_exceeded",
                "请改为选择单个资料，或调小资料范围后重试。",
            ),
        ) from exc
    except KnowledgeGraphExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_error_detail(
                "AI 知识图谱抽取失败。",
                "llm_extraction_failed",
                str(exc),
            ),
        ) from exc


@router.get(
    "/api/projects/{project_id}/knowledge-graph/extraction-runs",
    response_model=KnowledgeGraphRunList,
)
def list_knowledge_graph_extraction_runs(
    project_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
):
    try:
        items = service.list_runs(project_id, limit=limit)
        return KnowledgeGraphRunList(total=len(items), items=items)
    except KnowledgeGraphProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.get(
    "/api/projects/{project_id}/knowledge-graph/entities",
    response_model=KnowledgeGraphEntityList,
)
def list_knowledge_graph_entities(
    project_id: str,
    entity_status: KnowledgeGraphStatus | None = Query(default=None, alias="status"),
    entity_type: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
):
    try:
        items = service.list_entities(
            project_id,
            status=entity_status,
            entity_type=entity_type,
            keyword=keyword,
            limit=limit,
        )
        return KnowledgeGraphEntityList(total=len(items), items=items)
    except KnowledgeGraphProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.get(
    "/api/projects/{project_id}/knowledge-graph/relations",
    response_model=KnowledgeGraphRelationList,
)
def list_knowledge_graph_relations(
    project_id: str,
    relation_status: KnowledgeGraphStatus | None = Query(default=None, alias="status"),
    entity_id: str | None = Query(default=None),
    relation_type: KnowledgeGraphRelationType | None = Query(default=None),
    fact_status: KnowledgeGraphFactStatus | None = Query(default=None),
    source_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
):
    try:
        items = service.list_relations(
            project_id,
            status=relation_status,
            entity_id=entity_id,
            relation_type=relation_type,
            source_id=source_id,
            limit=limit,
        )
        if fact_status:
            items = [item for item in items if item.fact_status == fact_status]
        return KnowledgeGraphRelationList(total=len(items), items=items)
    except KnowledgeGraphProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/knowledge-graph/entities/{entity_id}/accept",
    response_model=KnowledgeGraphEntityRead,
)
def accept_knowledge_graph_entity(
    project_id: str,
    entity_id: str,
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
):
    try:
        return service.accept_entity(project_id, entity_id)
    except KnowledgeGraphEntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge graph entity not found") from exc


@router.post(
    "/api/projects/{project_id}/knowledge-graph/entities/{entity_id}/reject",
    response_model=KnowledgeGraphEntityRead,
)
def reject_knowledge_graph_entity(
    project_id: str,
    entity_id: str,
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
):
    try:
        return service.reject_entity(project_id, entity_id)
    except KnowledgeGraphEntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge graph entity not found") from exc


@router.post(
    "/api/projects/{project_id}/knowledge-graph/relations/{relation_id}/accept",
    response_model=KnowledgeGraphRelationRead,
)
def accept_knowledge_graph_relation(
    project_id: str,
    relation_id: str,
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
):
    try:
        return service.accept_relation(project_id, relation_id)
    except KnowledgeGraphRelationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge graph relation not found") from exc


@router.post(
    "/api/projects/{project_id}/knowledge-graph/relations/{relation_id}/reject",
    response_model=KnowledgeGraphRelationRead,
)
def reject_knowledge_graph_relation(
    project_id: str,
    relation_id: str,
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
):
    try:
        return service.reject_relation(project_id, relation_id)
    except KnowledgeGraphRelationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge graph relation not found") from exc


@router.get(
    "/api/projects/{project_id}/knowledge-graph/subgraph",
    response_model=KnowledgeGraphSubgraph,
)
def get_knowledge_graph_subgraph(
    project_id: str,
    graph_status: KnowledgeGraphStatus = Query(default="accepted", alias="status"),
    entity_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
):
    try:
        return service.get_subgraph(
            project_id,
            status=graph_status,
            entity_id=entity_id,
            limit=limit,
        )
    except KnowledgeGraphProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
