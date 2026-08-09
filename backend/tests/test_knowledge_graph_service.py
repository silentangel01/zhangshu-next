import json
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from app.models.knowledge_graph_entity import KnowledgeGraphEntity  # noqa: E402,F401
from app.models.knowledge_graph_evidence import KnowledgeGraphEvidence  # noqa: E402,F401
from app.models.knowledge_graph_extraction_run import (  # noqa: E402,F401
    KnowledgeGraphExtractionRun,
)
from app.models.knowledge_graph_relation import KnowledgeGraphRelation  # noqa: E402,F401
from app.models.knowledge_source import KnowledgeSource  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.schemas.knowledge_graph import KnowledgeGraphExtractionRunCreate  # noqa: E402
from app.services.knowledge_graph_extraction_service import (  # noqa: E402
    KnowledgeGraphExtractionChunkLimitError,
    KnowledgeGraphExtractionPrivacyNotConfirmedError,
    KnowledgeGraphExtractionService,
)
from app.services.knowledge_graph_service import KnowledgeGraphService  # noqa: E402


class FakeLLMProvider:
    model_name = "fake-llm"

    def __init__(self, response: str):
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def generate(self, prompt: str, context: str) -> str:
        return ""

    def summarize(self, texts: list[str], instruction: str) -> str:
        return ""

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def project(db_session):
    project = Project(id=str(uuid4()), title="知识图谱测试项目")
    db_session.add(project)
    db_session.commit()
    return project


def _seed_source_with_chunks(
    db_session,
    project_id: str,
    *,
    chunk_count: int = 1,
) -> KnowledgeSource:
    source = KnowledgeSource(
        id=str(uuid4()),
        project_id=project_id,
        title="势力设定",
        source_type="note",
        source_uri="",
        author=None,
        summary="",
        content="林岚是晨星会的成员。晨星会位于银湾城。",
        tags="",
        status="active",
        credibility="normal",
    )
    db_session.add(source)
    for index in range(chunk_count):
        db_session.add(
            KnowledgeChunk(
                id=str(uuid4()),
                project_id=project_id,
                source_id=source.id,
                chunk_index=index,
                heading="组织",
                content=f"林岚是晨星会的成员。晨星会位于银湾城。片段{index}",
                token_count=30,
                metadata_json="{}",
            )
        )
    db_session.commit()
    return source


def _fake_response() -> str:
    return json.dumps(
        {
            "items": [
                {
                    "subject": "林岚",
                    "subject_type": "character",
                    "predicate": "是成员",
                    "object": "晨星会",
                    "object_type": "organization",
                    "relation_type": "belongs_to",
                    "fact_status": "confirmed",
                    "confidence": 0.9,
                    "evidence": "林岚是晨星会的成员",
                },
                {
                    "subject": "晨星会",
                    "subject_type": "organization",
                    "predicate": "位于",
                    "object": "银湾城",
                    "object_type": "location",
                    "relation_type": "located_in",
                    "fact_status": "confirmed",
                    "confidence": 0.8,
                    "evidence": "晨星会位于银湾城",
                },
            ]
        },
        ensure_ascii=False,
    )


def test_extraction_creates_candidate_relations_with_evidence(db_session, project):
    source = _seed_source_with_chunks(db_session, project.id)
    llm = FakeLLMProvider(_fake_response())
    service = KnowledgeGraphExtractionService(db_session, llm)

    run = service.run_extraction(
        project.id,
        KnowledgeGraphExtractionRunCreate(
            scope="source",
            source_id=source.id,
            privacy_confirmed=True,
        ),
    )

    assert run.status == "completed"
    assert run.model_name == "fake-llm"
    assert run.processed_chunks == 1
    assert run.candidate_entity_count == 3
    assert run.candidate_relation_count == 2
    assert len(llm.calls) == 1

    graph = KnowledgeGraphService(db_session)
    relations = graph.list_relations(project.id, status="candidate")
    assert len(relations) == 2
    assert relations[0].evidence
    assert relations[0].evidence[0].source_id == source.id


def test_extraction_requires_privacy_confirmation(db_session, project):
    source = _seed_source_with_chunks(db_session, project.id)
    service = KnowledgeGraphExtractionService(db_session, FakeLLMProvider(_fake_response()))

    with pytest.raises(KnowledgeGraphExtractionPrivacyNotConfirmedError):
        service.run_extraction(
            project.id,
            KnowledgeGraphExtractionRunCreate(
                scope="source",
                source_id=source.id,
                privacy_confirmed=False,
            ),
        )


def test_extraction_enforces_chunk_limit(db_session, project):
    source = _seed_source_with_chunks(db_session, project.id, chunk_count=3)
    service = KnowledgeGraphExtractionService(db_session, FakeLLMProvider(_fake_response()))

    with pytest.raises(KnowledgeGraphExtractionChunkLimitError) as exc_info:
        service.run_extraction(
            project.id,
            KnowledgeGraphExtractionRunCreate(
                scope="source",
                source_id=source.id,
                max_chunks=2,
                privacy_confirmed=True,
            ),
        )

    assert exc_info.value.chunk_count == 3
    assert exc_info.value.max_chunks == 2


def test_accept_relation_also_accepts_candidate_entities(db_session, project):
    source = _seed_source_with_chunks(db_session, project.id)
    extraction = KnowledgeGraphExtractionService(
        db_session,
        FakeLLMProvider(_fake_response()),
    )
    extraction.run_extraction(
        project.id,
        KnowledgeGraphExtractionRunCreate(
            scope="source",
            source_id=source.id,
            privacy_confirmed=True,
        ),
    )

    graph = KnowledgeGraphService(db_session)
    relation = graph.list_relations(project.id, status="candidate")[0]
    accepted = graph.accept_relation(project.id, relation.id)

    assert accepted.status == "accepted"
    assert accepted.subject.status == "accepted"
    assert accepted.object.status == "accepted"

    subgraph = graph.get_subgraph(project.id)
    assert len(subgraph.edges) == 1
    assert len(subgraph.nodes) == 2


def test_duplicate_relation_reuses_existing_candidate(db_session, project):
    source = _seed_source_with_chunks(db_session, project.id)
    response = json.dumps(
        {
            "items": [
                {
                    "subject": "林岚",
                    "subject_type": "character",
                    "predicate": "是成员",
                    "object": "晨星会",
                    "object_type": "organization",
                    "relation_type": "belongs_to",
                    "confidence": 0.7,
                    "evidence": "林岚是晨星会的成员",
                },
                {
                    "subject": "林岚",
                    "subject_type": "character",
                    "predicate": "是成员",
                    "object": "晨星会",
                    "object_type": "organization",
                    "relation_type": "belongs_to",
                    "confidence": 0.9,
                    "evidence": "林岚是晨星会的成员",
                },
            ]
        },
        ensure_ascii=False,
    )
    extraction = KnowledgeGraphExtractionService(db_session, FakeLLMProvider(response))
    extraction.run_extraction(
        project.id,
        KnowledgeGraphExtractionRunCreate(
            scope="source",
            source_id=source.id,
            privacy_confirmed=True,
        ),
    )

    graph = KnowledgeGraphService(db_session)
    relations = graph.list_relations(project.id, status="candidate")
    assert len(relations) == 1
    assert relations[0].confidence == 0.9
    assert relations[0].source_count == 2
    assert len(relations[0].evidence) == 2
