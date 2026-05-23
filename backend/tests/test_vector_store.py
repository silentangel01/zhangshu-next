"""Tests for the vector store infrastructure."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.infrastructure.vector_store import SqliteVectorStore  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from app.models.knowledge_embedding import KnowledgeEmbedding  # noqa: E402
from app.models.knowledge_source import KnowledgeSource  # noqa: E402
from app.models.project import Project  # noqa: E402


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
def store(db_session):
    return SqliteVectorStore(db_session)


def _create_source_with_chunk(
    db_session, project_id, title, content, source_type="note", credibility="normal"
):
    """Helper to create a source with one chunk."""
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


# ---------- Upsert and Search ----------


class TestUpsertAndSearch:
    def test_upsert_and_search_returns_result(self, db_session, project, store):
        source, chunk = _create_source_with_chunk(
            db_session, project.id, "资料", "魔法体系内容"
        )
        vector = [1.0, 0.0, 0.0, 0.0]

        store.upsert(
            chunk_id=chunk.id,
            source_id=source.id,
            project_id=project.id,
            vector=vector,
            model_name="test-model",
            vector_dim=4,
        )

        results = store.search(vector, project.id, top_k=5)
        assert len(results) == 1
        assert results[0].chunk_id == chunk.id
        assert results[0].source_id == source.id
        assert abs(results[0].score - 1.0) < 1e-6

    def test_search_returns_empty_when_no_embeddings(self, db_session, project, store):
        results = store.search([1.0, 0.0], project.id)
        assert results == []

    def test_search_empty_when_project_mismatch(self, db_session, project, store):
        source, chunk = _create_source_with_chunk(
            db_session, project.id, "资料", "内容"
        )
        store.upsert(chunk.id, source.id, project.id, [1.0, 0.0], "test", 2)

        other_project_id = str(uuid4())
        results = store.search([1.0, 0.0], other_project_id)
        assert results == []


# ---------- Delete ----------


class TestDelete:
    def test_delete_removes_embedding(self, db_session, project, store):
        source, chunk = _create_source_with_chunk(
            db_session, project.id, "资料", "内容"
        )
        store.upsert(chunk.id, source.id, project.id, [1.0, 0.0], "test", 2)

        store.delete(chunk.id)

        results = store.search([1.0, 0.0], project.id)
        assert results == []

    def test_delete_by_source_removes_all(self, db_session, project, store):
        source1, chunk1 = _create_source_with_chunk(
            db_session, project.id, "资料1", "内容1"
        )
        source2, chunk2 = _create_source_with_chunk(
            db_session, project.id, "资料2", "内容2"
        )
        store.upsert(chunk1.id, source1.id, project.id, [1.0, 0.0], "test", 2)
        store.upsert(chunk2.id, source2.id, project.id, [0.0, 1.0], "test", 2)

        store.delete_by_source(source1.id)

        results = store.search([1.0, 0.0], project.id, top_k=10)
        assert len(results) == 1
        assert results[0].chunk_id == chunk2.id


# ---------- Filters ----------


class TestFilters:
    def test_filter_by_source_type(self, db_session, project, store):
        s1, c1 = _create_source_with_chunk(
            db_session, project.id, "笔记", "魔法笔记", source_type="note"
        )
        s2, c2 = _create_source_with_chunk(
            db_session, project.id, "书籍", "魔法书籍", source_type="book"
        )
        store.upsert(c1.id, s1.id, project.id, [1.0, 0.0], "test", 2)
        store.upsert(c2.id, s2.id, project.id, [0.9, 0.1], "test", 2)

        results = store.search([1.0, 0.0], project.id, filters={"source_type": "note"})
        assert len(results) == 1
        assert results[0].source_type == "note"

    def test_filter_by_credibility(self, db_session, project, store):
        s1, c1 = _create_source_with_chunk(
            db_session, project.id, "高可信", "高可信", credibility="high"
        )
        s2, c2 = _create_source_with_chunk(
            db_session, project.id, "低可信", "低可信", credibility="low"
        )
        store.upsert(c1.id, s1.id, project.id, [1.0, 0.0], "test", 2)
        store.upsert(c2.id, s2.id, project.id, [0.9, 0.1], "test", 2)

        results = store.search(
            [1.0, 0.0], project.id, filters={"credibility": "high"}
        )
        assert len(results) == 1
        assert results[0].source_credibility == "high"

    def test_filter_by_source_id(self, db_session, project, store):
        s1, c1 = _create_source_with_chunk(
            db_session, project.id, "资料1", "内容1"
        )
        s2, c2 = _create_source_with_chunk(
            db_session, project.id, "资料2", "内容2"
        )
        store.upsert(c1.id, s1.id, project.id, [1.0, 0.0], "test", 2)
        store.upsert(c2.id, s2.id, project.id, [0.9, 0.1], "test", 2)

        results = store.search(
            [1.0, 0.0], project.id, filters={"source_id": s1.id}
        )
        assert len(results) == 1
        assert results[0].source_id == s1.id


# ---------- Top-K and Ordering ----------


class TestTopKAndOrdering:
    def test_top_k_limits_results(self, db_session, project, store):
        for i in range(10):
            s, c = _create_source_with_chunk(
                db_session, project.id, f"资料{i}", f"内容{i}"
            )
            vec = [0.0] * 4
            vec[i % 4] = 1.0
            store.upsert(c.id, s.id, project.id, vec, "test", 4)

        results = store.search([1.0, 0.0, 0.0, 0.0], project.id, top_k=3)
        assert len(results) == 3

    def test_results_ordered_by_similarity(self, db_session, project, store):
        s1, c1 = _create_source_with_chunk(
            db_session, project.id, "最相似", "最相似内容"
        )
        s2, c2 = _create_source_with_chunk(
            db_session, project.id, "较相似", "较相似内容"
        )
        s3, c3 = _create_source_with_chunk(
            db_session, project.id, "不相似", "不相似内容"
        )

        store.upsert(c1.id, s1.id, project.id, [1.0, 0.0], "test", 2)
        store.upsert(c2.id, s2.id, project.id, [0.7, 0.7], "test", 2)
        store.upsert(c3.id, s3.id, project.id, [0.0, 1.0], "test", 2)

        results = store.search([1.0, 0.0], project.id, top_k=10)
        assert len(results) == 3
        assert results[0].chunk_id == c1.id
        assert results[0].score >= results[1].score
        assert results[1].score >= results[2].score


# ---------- Upsert Idempotency ----------


class TestUpsertIdempotency:
    def test_upsert_same_chunk_updates(self, db_session, project, store):
        source, chunk = _create_source_with_chunk(
            db_session, project.id, "资料", "内容"
        )

        store.upsert(chunk.id, source.id, project.id, [1.0, 0.0], "test", 2)
        store.upsert(chunk.id, source.id, project.id, [0.0, 1.0], "test", 2)

        results = store.search([0.0, 1.0], project.id, top_k=5)
        assert len(results) == 1
        assert abs(results[0].score - 1.0) < 1e-6
