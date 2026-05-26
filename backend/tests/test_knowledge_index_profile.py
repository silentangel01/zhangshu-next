"""Tests for the knowledge index profile model and repository."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.knowledge_index_profile import KnowledgeIndexProfile  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.repositories.knowledge_index_profile_repo import (  # noqa: E402
    KnowledgeIndexProfileRepository,
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
def repo(db_session):
    return KnowledgeIndexProfileRepository(db_session)


class TestGetByProject:
    def test_returns_none_when_missing(self, repo, project):
        result = repo.get_by_project(project.id)
        assert result is None

    def test_returns_profile_after_upsert(self, repo, project):
        repo.upsert(project.id, "local_basic_hash", "bigram-hash-v1", 256)
        profile = repo.get_by_project(project.id)
        assert profile is not None
        assert profile.provider_id == "local_basic_hash"
        assert profile.model_name == "bigram-hash-v1"
        assert profile.vector_dim == 256


class TestUpsert:
    def test_creates_new_profile(self, repo, project):
        profile = repo.upsert(project.id, "local_basic_hash", "bigram-hash-v1", 256)
        assert profile.id is not None
        assert profile.project_id == project.id
        assert profile.provider_id == "local_basic_hash"
        assert profile.created_at is not None

    def test_updates_existing_profile(self, repo, project):
        repo.upsert(project.id, "local_basic_hash", "bigram-hash-v1", 256)
        updated = repo.upsert(project.id, "dashscope_text_embedding_v4", "text-embedding-v4", 1024)
        assert updated.provider_id == "dashscope_text_embedding_v4"
        assert updated.model_name == "text-embedding-v4"
        assert updated.vector_dim == 1024

    def test_preserves_created_at(self, repo, project):
        first = repo.upsert(project.id, "local_basic_hash", "bigram-hash-v1", 256)
        created_at = first.created_at
        second = repo.upsert(project.id, "dashscope_text_embedding_v4", "text-embedding-v4", 1024)
        assert second.created_at == created_at
        assert second.updated_at >= created_at

    def test_unique_project_id(self, repo, project):
        repo.upsert(project.id, "local_basic_hash", "bigram-hash-v1", 256)
        # Second upsert should update, not create duplicate
        repo.upsert(project.id, "dashscope_text_embedding_v4", "text-embedding-v4", 1024)
        # Should still be only one profile for this project
        profile = repo.get_by_project(project.id)
        assert profile is not None
        assert profile.provider_id == "dashscope_text_embedding_v4"


class TestUpsertFullFields:
    def test_upsert_with_full_fields(self, repo, project):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        profile = repo.upsert(
            project.id,
            "dashscope_text_embedding_v4",
            "text-embedding-v4",
            1024,
            provider_type="cloud",
            display_name="云端精准索引",
            chunk_size="large",
            status="ready",
            last_refreshed_at=now,
            last_error=None,
        )
        assert profile.provider_type == "cloud"
        assert profile.display_name == "云端精准索引"
        assert profile.chunk_size == "large"
        assert profile.status == "ready"
        assert profile.last_refreshed_at is not None
        assert profile.last_error is None

    def test_upsert_default_values(self, repo, project):
        profile = repo.upsert(project.id, "local_basic_hash", "bigram-hash-v1", 256)
        assert profile.provider_type == "compat"
        assert profile.display_name == ""
        assert profile.chunk_size == "medium"
        assert profile.status == "ready"
        assert profile.last_refreshed_at is None
        assert profile.last_error is None


class TestMarkError:
    def test_mark_error(self, repo, project):
        repo.upsert(project.id, "local_basic_hash", "bigram-hash-v1", 256)
        repo.mark_error(project.id, "Something went wrong")

        profile = repo.get_by_project(project.id)
        assert profile is not None
        assert profile.status == "error"
        assert profile.last_error == "Something went wrong"

    def test_mark_error_no_profile(self, repo, project):
        # Should not raise when no profile exists
        repo.mark_error(project.id, "error")


class TestMarkStale:
    def test_mark_stale(self, repo, project):
        repo.upsert(project.id, "local_basic_hash", "bigram-hash-v1", 256)
        repo.mark_stale(project.id)

        profile = repo.get_by_project(project.id)
        assert profile is not None
        assert profile.status == "stale"

    def test_mark_stale_no_profile(self, repo, project):
        # Should not raise when no profile exists
        repo.mark_stale(project.id)
