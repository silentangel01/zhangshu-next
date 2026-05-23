"""Tests for the AI Summary service."""

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
from app.services.ai_summary_service import (  # noqa: E402
    AISummaryService,
    SummaryInvalidModeError,
    SummaryProjectNotFoundError,
)
from app.services.knowledge_embedding_service import KnowledgeEmbeddingService  # noqa: E402


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
    return AISummaryService(db_session, llm_provider=StubLLMProvider())


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
            heading="",
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


# ---------- Summarize ----------


class TestSummarize:
    def test_summarize_returns_response(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "魔法体系包括元素魔法。"
        )

        response = service.summarize(
            project.id, source_ids=[source.id]
        )

        assert response.summary
        assert response.sources_used >= 1
        assert response.model == "stub-v1"

    def test_summarize_contains_stub_marker(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "魔法体系内容。"
        )

        response = service.summarize(
            project.id, source_ids=[source.id]
        )

        assert "[AI 模型尚未接入]" in response.summary

    def test_summarize_is_draft_always_true(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "内容。"
        )

        response = service.summarize(
            project.id, source_ids=[source.id]
        )

        assert response.is_draft is True

    def test_summarize_with_topic(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "魔法体系内容。"
        )
        _index_source(db_session, source)

        response = service.summarize(
            project.id, topic="魔法", mode="keyword"
        )

        # Topic should be reflected in the summary instruction
        # (stub provider echoes instruction in its output)
        assert response.summary

    def test_summarize_with_source_ids_filters(self, db_session, project, service):
        source1, _ = _create_source_with_chunks(
            db_session, project.id, "资料A", "关于A的内容。"
        )
        source2, _ = _create_source_with_chunks(
            db_session, project.id, "资料B", "关于B的内容。"
        )

        response = service.summarize(
            project.id, source_ids=[source1.id]
        )

        assert response.sources_used >= 1
        assert "资料A" in response.source_titles
        assert "资料B" not in response.source_titles

    def test_summarize_empty_project_no_error(self, db_session, project, service):
        response = service.summarize(project.id)

        assert response.summary
        assert response.sources_used == 0
        assert "[AI 模型尚未接入]" in response.summary

    def test_summarize_project_not_found(self, service):
        with pytest.raises(SummaryProjectNotFoundError):
            service.summarize(str(uuid4()))

    def test_summarize_invalid_mode(self, db_session, project, service):
        with pytest.raises(SummaryInvalidModeError):
            service.summarize(project.id, topic="test", mode="invalid_mode")

    def test_summarize_source_titles_collected(self, db_session, project, service):
        source1, _ = _create_source_with_chunks(
            db_session, project.id, "资料Alpha", "内容1。"
        )
        source2, _ = _create_source_with_chunks(
            db_session, project.id, "资料Beta", "内容2。"
        )

        response = service.summarize(
            project.id, source_ids=[source1.id, source2.id]
        )

        assert "资料Alpha" in response.source_titles
        assert "资料Beta" in response.source_titles
