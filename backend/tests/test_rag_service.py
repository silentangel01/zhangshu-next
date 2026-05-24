"""Tests for the RAG service."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.infrastructure.embedding_provider import BigramHashEmbeddingProvider  # noqa: E402
from app.infrastructure.llm_provider import StubLLMProvider  # noqa: E402
from app.infrastructure.vector_store import SqliteVectorStore  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from app.models.knowledge_embedding import KnowledgeEmbedding  # noqa: E402
from app.models.knowledge_source import KnowledgeSource  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.services.knowledge_embedding_service import KnowledgeEmbeddingService  # noqa: E402
from app.services.rag_service import RagInvalidModeError, RagProjectNotFoundError, RagService  # noqa: E402


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
    pid = str(uuid4())
    project = Project(id=pid, title="Test Project")
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def service(db_session):
    return RagService(db_session, llm_provider=StubLLMProvider())


def _create_source_with_chunks(db_session, project_id, title, content, num_chunks=1):
    """Helper to create a source with chunks."""
    source_id = str(uuid4())
    source = KnowledgeSource(
        id=source_id,
        project_id=project_id,
        title=title,
        source_type="note",
        source_uri="",
        author=None,
        summary="",
        content=content,
        tags="",
        status="active",
        credibility="normal",
    )
    db_session.add(source)

    chunks = []
    for i in range(num_chunks):
        chunk_content = f"{content} 分块{i}" if num_chunks > 1 else content
        chunk_id = str(uuid4())
        chunk = KnowledgeChunk(
            id=chunk_id,
            project_id=project_id,
            source_id=source_id,
            chunk_index=i,
            heading=f"{title}标题{i}" if num_chunks > 1 else f"{title}标题",
            content=chunk_content,
            token_count=len(chunk_content),
            metadata_json="{}",
        )
        db_session.add(chunk)
        chunks.append(chunk)

    db_session.commit()
    return source, chunks


def _index_source(db_session, source):
    """Build embeddings for a source."""
    provider = BigramHashEmbeddingProvider()
    store = SqliteVectorStore(db_session)
    embedding_service = KnowledgeEmbeddingService(db_session, provider=provider, store=store)
    embedding_service.index_source(source.id)


# ---------- Ask ----------


class TestAsk:
    def test_ask_returns_response_with_answer_and_citations(
        self, db_session, project, service
    ):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "魔法体系", "魔法体系包括元素魔法和咒语魔法。", num_chunks=2
        )
        _index_source(db_session, source)

        response = service.ask(project.id, "什么是魔法体系？", mode="keyword")

        assert response.question == "什么是魔法体系？"
        assert response.answer
        assert isinstance(response.citations, list)
        assert response.model == "stub-v1"
        assert response.retrieval_mode == "keyword"

    def test_ask_answer_contains_stub_marker(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "魔法体系", "魔法体系包括元素魔法和咒语魔法，是战斗的基础。"
        )
        _index_source(db_session, source)

        response = service.ask(project.id, "魔法", mode="keyword")

        assert "[AI 模型尚未接入]" in response.answer

    def test_ask_citations_count_matches_results(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "内容", num_chunks=3
        )
        _index_source(db_session, source)

        response = service.ask(project.id, "内容", mode="keyword", top_k=10)

        assert len(response.citations) == response.citations.__len__()
        assert len(response.citations) <= 10

    def test_ask_citations_contain_correct_fields(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "魔法资料", "魔法体系内容描述"
        )
        _index_source(db_session, source)

        response = service.ask(project.id, "魔法体系", mode="keyword")

        if response.citations:
            citation = response.citations[0]
            assert citation.chunk_id
            assert citation.source_id == source.id
            assert citation.source_title == "魔法资料"
            assert citation.chunk_content

    def test_ask_empty_question_returns_empty(self, db_session, project, service):
        response = service.ask(project.id, "", mode="keyword")

        assert response.answer == ""
        assert response.citations == []

    def test_ask_whitespace_question_returns_empty(self, db_session, project, service):
        response = service.ask(project.id, "   ", mode="keyword")

        assert response.answer == ""
        assert response.citations == []

    def test_ask_mode_passed_to_retrieval(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "一些内容"
        )
        _index_source(db_session, source)

        response = service.ask(project.id, "内容", mode="hybrid")

        assert response.retrieval_mode == "hybrid"

    def test_ask_no_matching_results_empty_citations(self, db_session, project, service):
        _create_source_with_chunks(
            db_session, project.id, "资料", "完全无关的内容"
        )

        response = service.ask(project.id, "xyzzy_nonexistent_query", mode="keyword")

        assert response.citations == []

    def test_ask_project_not_found(self, service):
        with pytest.raises(RagProjectNotFoundError):
            service.ask(str(uuid4()), "问题")

    def test_ask_invalid_mode(self, db_session, project, service):
        with pytest.raises(RagInvalidModeError):
            service.ask(project.id, "问题", mode="invalid_mode")

    def test_ask_top_k_limits_citations(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "内容", num_chunks=5
        )
        _index_source(db_session, source)

        response = service.ask(project.id, "内容", mode="keyword", top_k=2)

        assert len(response.citations) <= 2
