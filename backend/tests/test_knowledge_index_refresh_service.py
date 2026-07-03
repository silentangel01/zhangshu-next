"""Tests for the knowledge index refresh service."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from app.models.knowledge_embedding import KnowledgeEmbedding  # noqa: E402
from app.models.knowledge_source import KnowledgeSource  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.services.knowledge_index_refresh_service import (  # noqa: E402
    KnowledgeIndexRefreshProjectNotFoundError,
    KnowledgeIndexRefreshService,
    KnowledgeIndexRefreshSourceNotFoundError,
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
    return KnowledgeIndexRefreshService(db_session)


def _create_source(db_session, project_id, title, content):
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
    db_session.commit()
    return source


# ---------- Refresh Project ----------


class TestRefreshProject:
    def test_refresh_project_rebuilds_chunks_and_index(
        self, db_session, project, service
    ):
        content = "段落一。\n\n段落二。\n\n段落三。" * 20
        _create_source(db_session, project.id, "资料A", content)
        _create_source(db_session, project.id, "资料B", content)

        result = service.refresh_project(project.id)

        assert result.source_count == 2
        assert result.chunk_count > 0
        assert result.indexed_count > 0
        assert result.chunk_size == "medium"
        assert result.model_name

    def test_refresh_project_with_chunk_size(self, db_session, project, service):
        content = "段落内容。\n\n" * 30
        _create_source(db_session, project.id, "资料", content)

        result = service.refresh_project(project.id, chunk_size="small")

        assert result.chunk_size == "small"
        assert result.chunk_count > 0

    def test_refresh_project_not_found(self, service):
        with pytest.raises(KnowledgeIndexRefreshProjectNotFoundError):
            service.refresh_project(str(uuid4()))

    def test_refresh_project_no_sources(self, db_session, project, service):
        result = service.refresh_project(project.id)

        assert result.source_count == 0
        assert result.chunk_count == 0
        assert result.indexed_count == 0
        assert len(result.warnings) > 0

    def test_refresh_project_empty_source_warning(
        self, db_session, project, service
    ):
        _create_source(db_session, project.id, "空资料", "")
        _create_source(db_session, project.id, "有内容", "有内容的资料。" * 20)

        result = service.refresh_project(project.id)

        assert result.source_count == 2
        assert any("空资料" in w for w in result.warnings)


# ---------- Refresh Source ----------


class TestRefreshSource:
    def test_refresh_source_rebuilds_chunks_and_index(
        self, db_session, project, service
    ):
        content = "段落一。\n\n段落二。\n\n段落三。" * 20
        source = _create_source(db_session, project.id, "单资料", content)

        result = service.refresh_source(source.id)

        assert result.source_count == 1
        assert result.chunk_count > 0
        assert result.indexed_count > 0
        assert result.chunk_size == "medium"

    def test_refresh_source_with_chunk_size(self, db_session, project, service):
        content = "段落内容。\n\n" * 30
        source = _create_source(db_session, project.id, "资料", content)

        result = service.refresh_source(source.id, chunk_size="large")

        assert result.chunk_size == "large"

    def test_refresh_source_not_found(self, service):
        with pytest.raises(KnowledgeIndexRefreshSourceNotFoundError):
            service.refresh_source(str(uuid4()))

    def test_refresh_source_empty_content(self, db_session, project, service):
        source = _create_source(db_session, project.id, "空资料", "")

        result = service.refresh_source(source.id)

        assert result.source_count == 1
        assert result.chunk_count == 0
        assert result.indexed_count == 0
        assert len(result.warnings) > 0

    def test_refresh_source_replaces_old_embeddings(
        self, db_session, project, service
    ):
        content = "段落内容。\n\n" * 30
        source = _create_source(db_session, project.id, "资料", content)

        # First refresh
        service.refresh_source(source.id)
        old_embeddings = db_session.query(KnowledgeEmbedding).filter_by(
            source_id=source.id
        ).all()
        assert len(old_embeddings) > 0
        old_ids = {e.id for e in old_embeddings}

        # Expunge old objects before they get invalidated by deletion
        db_session.expunge_all()

        # Second refresh should replace embeddings
        service.refresh_source(source.id)
        new_embeddings = db_session.query(KnowledgeEmbedding).filter_by(
            source_id=source.id
        ).all()
        assert len(new_embeddings) > 0
        new_ids = {e.id for e in new_embeddings}
        # Old embeddings should be gone, replaced by new ones
        assert old_ids != new_ids


# ---------- Provider Integration ----------


class TestProviderIntegration:
    def test_refresh_project_creates_profile(self, db_session, project, service):
        _create_source(db_session, project.id, "资料", "内容。" * 50)
        service.refresh_project(project.id)

        profile = service.profile_repo.get_by_project(project.id)
        assert profile is not None
        assert profile.provider_id == "local_basic_hash"
        assert profile.model_name == "bigram-hash-v2"
        assert profile.vector_dim == 256

    def test_refresh_project_returns_provider_id(self, db_session, project, service):
        _create_source(db_session, project.id, "资料", "内容。" * 50)
        result = service.refresh_project(project.id)
        assert result.provider_id == "local_basic_hash"

    def test_refresh_source_conflict_raises(self, db_session, project, service):
        _create_source(db_session, project.id, "资料", "内容。" * 50)
        # Create a profile with a specific provider
        service.profile_repo.upsert(
            project.id, "local_basic_hash", "bigram-hash-v1", 256
        )

        # Attempt source-scope refresh with a different provider
        from app.services.knowledge_index_refresh_service import (
            KnowledgeIndexProviderConflictError,
        )

        source = db_session.query(KnowledgeSource).first()
        with pytest.raises(KnowledgeIndexProviderConflictError):
            service.refresh_source(
                source.id,
                provider_id="dashscope_text_embedding_v4",
            )

    def test_refresh_cloud_without_privacy_raises(self, db_session, project, service, monkeypatch):
        monkeypatch.setenv("ZHANGSHU_DASHSCOPE_API_KEY", "test-key")
        from app.services.knowledge_index_refresh_service import (
            KnowledgeIndexPrivacyRequiredError,
        )

        with pytest.raises(KnowledgeIndexPrivacyRequiredError):
            service.refresh_project(
                project.id,
                provider_id="dashscope_text_embedding_v4",
                privacy_confirmed=False,
            )

    def test_refresh_unavailable_provider_raises(self, db_session, project, service):
        from app.services.knowledge_index_refresh_service import (
            KnowledgeIndexProviderUnavailableError,
        )

        with pytest.raises(KnowledgeIndexProviderUnavailableError):
            service.refresh_project(
                project.id,
                provider_id="local_bge_small_zh",
            )

    def test_refresh_project_writes_full_profile(self, db_session, project, service):
        _create_source(db_session, project.id, "资料", "内容。" * 50)
        result = service.refresh_project(project.id, chunk_size="large")

        profile = service.profile_repo.get_by_project(project.id)
        assert profile is not None
        assert profile.provider_id == "local_basic_hash"
        assert profile.provider_type == "compat"
        assert profile.display_name == "本地基础索引"
        assert profile.model_name == "bigram-hash-v2"
        assert profile.vector_dim == 256
        assert profile.chunk_size == "large"
        assert profile.status == "ready"
        assert profile.last_refreshed_at is not None
        assert profile.last_error is None
        assert result.profile_status == "ready"

    def test_refresh_source_creates_profile_when_missing(
        self, db_session, project, service
    ):
        source = _create_source(db_session, project.id, "资料", "内容。" * 50)
        # No profile exists yet
        assert service.profile_repo.get_by_project(project.id) is None

        service.refresh_source(source.id)

        profile = service.profile_repo.get_by_project(project.id)
        assert profile is not None
        assert profile.provider_id == "local_basic_hash"
        assert profile.status == "ready"
