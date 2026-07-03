"""Tests for the unified retrieval service (keyword, semantic, hybrid modes)."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.infrastructure.embedding_provider import BigramHashEmbeddingProvider  # noqa: E402
from app.infrastructure.vector_store import SqliteVectorStore  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from app.models.knowledge_embedding import KnowledgeEmbedding  # noqa: E402
from app.models.knowledge_source import KnowledgeSource  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.services.knowledge_embedding_service import KnowledgeEmbeddingService  # noqa: E402
from app.services.retrieval_service import (  # noqa: E402
    RetrievalInvalidModeError,
    RetrievalProjectNotFoundError,
    RetrievalService,
)


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
    provider = BigramHashEmbeddingProvider()
    store = SqliteVectorStore(db_session)
    return RetrievalService(db_session, provider=provider, store=store)


@pytest.fixture
def embedding_service(db_session):
    provider = BigramHashEmbeddingProvider()
    store = SqliteVectorStore(db_session)
    return KnowledgeEmbeddingService(db_session, provider=provider, store=store)


def _create_source_with_chunks(
    db_session, project_id, title, content, source_type="note", credibility="normal"
):
    source_id = str(uuid4())
    source = KnowledgeSource(
        id=source_id,
        project_id=project_id,
        title=title,
        source_type=source_type,
        source_uri="",
        author=None,
        summary="",
        content=content,
        tags="",
        status="active",
        credibility=credibility,
    )
    db_session.add(source)

    chunk_id = str(uuid4())
    chunk = KnowledgeChunk(
        id=chunk_id,
        project_id=project_id,
        source_id=source_id,
        chunk_index=0,
        heading="",
        content=content,
        token_count=len(content),
        metadata_json="{}",
    )
    db_session.add(chunk)
    db_session.commit()

    return source, chunk


# ---------- Mode Validation ----------


class TestModeValidation:
    def test_invalid_mode_raises_error(self, project, service):
        with pytest.raises(RetrievalInvalidModeError):
            service.search(project.id, "query", mode="invalid")

    def test_project_not_found(self, service):
        with pytest.raises(RetrievalProjectNotFoundError):
            service.search(str(uuid4()), "query", mode="keyword")


# ---------- Keyword Mode ----------


class TestKeywordMode:
    def test_keyword_mode_finds_match(self, db_session, project, service):
        _create_source_with_chunks(
            db_session, project.id, "魔法资料", "这是关于魔法体系的说明"
        )

        result = service.search(project.id, "魔法", mode="keyword")

        assert result.mode == "keyword"
        assert result.total == 1
        assert "魔法" in result.results[0].matched_snippet

    def test_keyword_mode_empty_query(self, project, service):
        result = service.search(project.id, "", mode="keyword")
        assert result.total == 0
        assert result.mode == "keyword"


# ---------- Semantic Mode ----------


class TestSemanticMode:
    def test_semantic_mode_with_index(self, db_session, project, service, embedding_service):
        source, chunk = _create_source_with_chunks(
            db_session, project.id, "魔法资料", "这是关于魔法体系的详细说明文档"
        )
        embedding_service.index_source(source.id)

        result = service.search(project.id, "魔法体系", mode="semantic")

        assert result.mode == "semantic"
        assert result.total >= 1
        assert result.results[0].relevance_score is not None

    def test_semantic_mode_without_index(self, db_session, project, service):
        _create_source_with_chunks(
            db_session, project.id, "魔法资料", "这是关于魔法体系的说明"
        )

        result = service.search(project.id, "魔法", mode="semantic")

        assert result.mode == "semantic"
        assert result.total == 0

    def test_semantic_mode_empty_query(self, project, service):
        result = service.search(project.id, "", mode="semantic")
        assert result.total == 0
        assert result.mode == "semantic"

    def test_semantic_results_ordered_by_score(self, db_session, project, service, embedding_service):
        s1, c1 = _create_source_with_chunks(
            db_session, project.id, "魔法详解", "魔法体系的详细说明文档内容包括各种魔法分类"
        )
        s2, c2 = _create_source_with_chunks(
            db_session, project.id, "科技说明", "科技发展历史文档记录了人类进步"
        )
        embedding_service.index_source(s1.id)
        embedding_service.index_source(s2.id)

        result = service.search(project.id, "魔法体系分类", mode="semantic")

        if result.total >= 2:
            assert result.results[0].relevance_score >= result.results[1].relevance_score


# ---------- Hybrid Mode ----------


class TestHybridMode:
    def test_hybrid_combines_results(self, db_session, project, service, embedding_service):
        s1, c1 = _create_source_with_chunks(
            db_session, project.id, "魔法关键词", "这里包含魔法关键词的内容"
        )
        s2, c2 = _create_source_with_chunks(
            db_session, project.id, "魔法语义", "魔法体系的语义相关内容"
        )
        embedding_service.index_source(s1.id)
        embedding_service.index_source(s2.id)

        result = service.search(project.id, "魔法", mode="hybrid")

        assert result.mode == "hybrid"
        assert result.total >= 1

    def test_hybrid_deduplicates(self, db_session, project, service, embedding_service):
        source, chunk = _create_source_with_chunks(
            db_session, project.id, "魔法资料", "魔法体系的详细说明魔法魔法"
        )
        embedding_service.index_source(source.id)

        result = service.search(project.id, "魔法", mode="hybrid")

        # Same chunk should appear only once even if both modes find it
        chunk_ids = [r.chunk_id for r in result.results]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_hybrid_empty_query(self, project, service):
        result = service.search(project.id, "", mode="hybrid")
        assert result.total == 0
        assert result.mode == "hybrid"


# ---------- Filters in Semantic Mode ----------


class TestSemanticFilters:
    def test_semantic_filter_by_source_type(self, db_session, project, service, embedding_service):
        s1, c1 = _create_source_with_chunks(
            db_session, project.id, "笔记", "魔法笔记内容", source_type="note"
        )
        s2, c2 = _create_source_with_chunks(
            db_session, project.id, "书籍", "魔法书籍内容", source_type="book"
        )
        embedding_service.index_source(s1.id)
        embedding_service.index_source(s2.id)

        result = service.search(
            project.id, "魔法", mode="semantic", source_type="note"
        )

        for r in result.results:
            assert r.source_type == "note"


# ---------- v1 / v2 Isolation ----------


class TestV1V2Isolation:
    """Old v1 embeddings must not be returned when the provider has upgraded to v2."""

    def test_old_v1_embeddings_not_returned_by_v2_query(
        self, db_session, project, service
    ):
        """Semantic search with v2 provider should not find v1 embeddings."""
        source, chunk = _create_source_with_chunks(
            db_session, project.id, "魔法资料", "这是关于魔法体系的详细说明"
        )

        # Insert a stale v1 embedding directly into the DB
        from app.models.knowledge_embedding import KnowledgeEmbedding

        old_embedding = KnowledgeEmbedding(
            id=str(uuid4()),
            chunk_id=chunk.id,
            source_id=source.id,
            project_id=project.id,
            model_name="bigram-hash-v1",
            vector_dim=256,
            vector_json="[0.1] * 256",
        )
        db_session.add(old_embedding)
        db_session.commit()

        # v2 provider should not find the v1 embedding
        result = service.search(project.id, "魔法体系", mode="semantic")
        assert result.total == 0
        assert result.mode == "semantic"
