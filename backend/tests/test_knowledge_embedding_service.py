"""Tests for the knowledge embedding service."""

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
from app.services.knowledge_embedding_service import (  # noqa: E402
    EmbeddingChunkNotFoundError,
    EmbeddingProjectNotFoundError,
    EmbeddingSourceNotFoundError,
    KnowledgeEmbeddingService,
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
    return KnowledgeEmbeddingService(db_session, provider=provider, store=store)


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


# ---------- Index Source ----------


class TestIndexSource:
    def test_index_source_creates_embeddings(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "魔法体系内容", num_chunks=3
        )

        count = service.index_source(source.id)

        assert count == 3
        # Verify embeddings exist in database
        embeddings = db_session.query(KnowledgeEmbedding).filter_by(
            source_id=source.id
        ).all()
        assert len(embeddings) == 3

    def test_index_source_empty_content(self, db_session, project, service):
        source_id = str(uuid4())
        source = KnowledgeSource(
            id=source_id,
            project_id=project.id,
            title="空资料",
            source_type="note",
            source_uri="",
            author=None,
            summary="",
            content="",
            tags="",
            status="active",
            credibility="normal",
        )
        db_session.add(source)
        db_session.commit()

        count = service.index_source(source.id)
        assert count == 0

    def test_index_source_not_found(self, service):
        with pytest.raises(EmbeddingSourceNotFoundError):
            service.index_source(str(uuid4()))


# ---------- Index Chunk ----------


class TestIndexChunk:
    def test_index_chunk_creates_embedding(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "魔法体系内容"
        )

        service.index_chunk(chunks[0].id)

        embedding = db_session.query(KnowledgeEmbedding).filter_by(
            chunk_id=chunks[0].id
        ).first()
        assert embedding is not None
        assert embedding.model_name == "bigram-hash-v1"
        assert embedding.vector_dim == 256

    def test_index_chunk_not_found(self, service):
        with pytest.raises(EmbeddingChunkNotFoundError):
            service.index_chunk(str(uuid4()))


# ---------- Rebuild Project Index ----------


class TestRebuildProjectIndex:
    def test_rebuild_indexes_all_chunks(self, db_session, project, service):
        _create_source_with_chunks(
            db_session, project.id, "资料1", "内容1", num_chunks=2
        )
        _create_source_with_chunks(
            db_session, project.id, "资料2", "内容2", num_chunks=3
        )

        count = service.rebuild_project_index(project.id)

        assert count == 5
        embeddings = db_session.query(KnowledgeEmbedding).filter_by(
            project_id=project.id
        ).all()
        assert len(embeddings) == 5

    def test_rebuild_replaces_old_embeddings(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "旧内容"
        )

        # First index
        service.index_source(source.id)
        old_embeddings = db_session.query(KnowledgeEmbedding).filter_by(
            source_id=source.id
        ).all()
        assert len(old_embeddings) == 1

        # Rebuild
        count = service.rebuild_project_index(project.id)

        assert count == 1
        embeddings = db_session.query(KnowledgeEmbedding).filter_by(
            project_id=project.id
        ).all()
        assert len(embeddings) == 1
        # Should be new embeddings (different IDs)
        assert embeddings[0].id != old_embeddings[0].id

    def test_rebuild_project_not_found(self, service):
        with pytest.raises(EmbeddingProjectNotFoundError):
            service.rebuild_project_index(str(uuid4()))

    def test_rebuild_empty_project(self, db_session, project, service):
        count = service.rebuild_project_index(project.id)
        assert count == 0


# ---------- Get Index Status ----------


class TestGetIndexStatus:
    def test_status_no_embeddings(self, db_session, project, service):
        _create_source_with_chunks(
            db_session, project.id, "资料", "内容", num_chunks=3
        )

        status = service.get_index_status(project.id)

        assert status.total_chunks == 3
        assert status.indexed_chunks == 0
        assert status.unindexed_chunks == 3
        assert status.model_name == "bigram-hash-v1"

    def test_status_partial_index(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "内容", num_chunks=3
        )

        # Index only first chunk
        service.index_chunk(chunks[0].id)

        status = service.get_index_status(project.id)

        assert status.total_chunks == 3
        assert status.indexed_chunks == 1
        assert status.unindexed_chunks == 2

    def test_status_fully_indexed(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "内容", num_chunks=3
        )

        service.index_source(source.id)

        status = service.get_index_status(project.id)

        assert status.total_chunks == 3
        assert status.indexed_chunks == 3
        assert status.unindexed_chunks == 0

    def test_status_project_not_found(self, service):
        with pytest.raises(EmbeddingProjectNotFoundError):
            service.get_index_status(str(uuid4()))


# ---------- Remove Source Embeddings ----------


class TestRemoveSourceEmbeddings:
    def test_remove_deletes_embeddings(self, db_session, project, service):
        source, chunks = _create_source_with_chunks(
            db_session, project.id, "资料", "内容", num_chunks=3
        )
        service.index_source(source.id)

        service.remove_source_embeddings(source.id)

        embeddings = db_session.query(KnowledgeEmbedding).filter_by(
            source_id=source.id
        ).all()
        assert len(embeddings) == 0

    def test_remove_nonexistent_source_no_error(self, db_session, project, service):
        # Should not raise
        service.remove_source_embeddings(str(uuid4()))
