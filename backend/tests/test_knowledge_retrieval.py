"""Tests for the knowledge retrieval service."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from app.models.knowledge_source import KnowledgeSource  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.services.knowledge_retrieval_service import (  # noqa: E402
    KnowledgeRetrievalProjectNotFoundError,
    KnowledgeRetrievalService,
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
    return KnowledgeRetrievalService(db_session)


def _create_source_with_chunks(
    db_session, project_id, title, content, source_type="note", credibility="normal", tags=""
):
    """Helper to create a source with auto-generated chunks."""
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
        tags=tags,
        status="active",
        credibility=credibility,
    )
    db_session.add(source)

    # Create chunks manually (simplified version of service chunking)
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


# ---------- Project Not Found ----------


class TestProjectNotFound:
    def test_search_raises_when_project_missing(self, service):
        with pytest.raises(KnowledgeRetrievalProjectNotFoundError):
            service.search_chunks(str(uuid4()), "keyword")


# ---------- Basic Search ----------


class TestBasicSearch:
    def test_search_finds_matching_chunk(self, db_session, project, service):
        content = "这是一个关于魔法体系的详细说明文档。"
        _create_source_with_chunks(db_session, project.id, "魔法资料", content)

        result = service.search_chunks(project.id, "魔法")

        assert result.total == 1
        assert result.keyword == "魔法"
        assert len(result.results) == 1
        assert "魔法" in result.results[0].matched_snippet

    def test_search_returns_empty_for_no_match(self, db_session, project, service):
        _create_source_with_chunks(db_session, project.id, "历史资料", "这是历史记录。")

        result = service.search_chunks(project.id, "魔法")

        assert result.total == 0
        assert len(result.results) == 0

    def test_search_empty_keyword_returns_empty(self, db_session, project, service):
        _create_source_with_chunks(db_session, project.id, "资料", "内容")

        result = service.search_chunks(project.id, "")

        assert result.total == 0
        assert len(result.results) == 0

    def test_search_whitespace_keyword_returns_empty(self, db_session, project, service):
        _create_source_with_chunks(db_session, project.id, "资料", "内容")

        result = service.search_chunks(project.id, "   ")

        assert result.total == 0
        assert len(result.results) == 0


# ---------- Context Extraction ----------


class TestContextExtraction:
    def test_extracts_context_around_match(self, db_session, project, service):
        content = "这是前文内容。这里提到了魔法体系的详细说明。这是后文内容。"
        _create_source_with_chunks(db_session, project.id, "资料", content)

        result = service.search_chunks(project.id, "魔法")

        assert result.total == 1
        chunk_result = result.results[0]
        assert chunk_result.matched_snippet == "魔法"
        assert "魔法" in chunk_result.context_before or len(chunk_result.context_before) > 0
        assert len(chunk_result.context_after) > 0

    def test_context_at_content_start(self, db_session, project, service):
        content = "魔法体系是这个世界的核心。"
        _create_source_with_chunks(db_session, project.id, "资料", content)

        result = service.search_chunks(project.id, "魔法")

        assert result.total == 1
        chunk_result = result.results[0]
        assert chunk_result.matched_snippet == "魔法"
        assert len(chunk_result.context_before) == 0 or chunk_result.context_before == ""

    def test_context_at_content_end(self, db_session, project, service):
        content = "这个世界的核心是魔法"
        _create_source_with_chunks(db_session, project.id, "资料", content)

        result = service.search_chunks(project.id, "魔法")

        assert result.total == 1
        chunk_result = result.results[0]
        assert chunk_result.matched_snippet == "魔法"
        assert len(chunk_result.context_after) == 0 or chunk_result.context_after == ""


# ---------- Filters ----------


class TestFilters:
    def test_filter_by_source_type(self, db_session, project, service):
        _create_source_with_chunks(
            db_session, project.id, "笔记", "魔法笔记", source_type="note"
        )
        _create_source_with_chunks(
            db_session, project.id, "书籍", "魔法书籍", source_type="book"
        )

        result = service.search_chunks(project.id, "魔法", source_type="note")

        assert result.total == 1
        assert result.results[0].source_type == "note"
        assert result.results[0].source_title == "笔记"

    def test_filter_by_credibility(self, db_session, project, service):
        _create_source_with_chunks(
            db_session, project.id, "高可信", "高可信魔法", credibility="high"
        )
        _create_source_with_chunks(
            db_session, project.id, "低可信", "低可信魔法", credibility="low"
        )

        result = service.search_chunks(project.id, "魔法", credibility="high")

        assert result.total == 1
        assert result.results[0].source_credibility == "high"

    def test_filter_by_tag(self, db_session, project, service):
        _create_source_with_chunks(
            db_session, project.id, "有标签", "有标签魔法", tags="魔法,重要"
        )
        _create_source_with_chunks(
            db_session, project.id, "无标签", "无标签魔法", tags=""
        )

        result = service.search_chunks(project.id, "魔法", tag="魔法")

        assert result.total == 1
        assert result.results[0].source_title == "有标签"

    def test_filter_by_source_id(self, db_session, project, service):
        source1, _ = _create_source_with_chunks(
            db_session, project.id, "资料1", "资料1魔法"
        )
        _create_source_with_chunks(db_session, project.id, "资料2", "资料2魔法")

        result = service.search_chunks(project.id, "魔法", source_id=source1.id)

        assert result.total == 1
        assert result.results[0].source_id == source1.id

    def test_multiple_filters_combined(self, db_session, project, service):
        _create_source_with_chunks(
            db_session,
            project.id,
            "匹配",
            "匹配魔法",
            source_type="note",
            credibility="high",
        )
        _create_source_with_chunks(
            db_session,
            project.id,
            "不匹配类型",
            "不匹配类型魔法",
            source_type="book",
            credibility="high",
        )
        _create_source_with_chunks(
            db_session,
            project.id,
            "不匹配可信度",
            "不匹配可信度魔法",
            source_type="note",
            credibility="low",
        )

        result = service.search_chunks(
            project.id, "魔法", source_type="note", credibility="high"
        )

        assert result.total == 1
        assert result.results[0].source_title == "匹配"


# ---------- Limit ----------


class TestLimit:
    def test_respects_limit_parameter(self, db_session, project, service):
        for i in range(10):
            _create_source_with_chunks(
                db_session, project.id, f"资料{i}", f"资料{i}魔法"
            )

        result = service.search_chunks(project.id, "魔法", limit=5)

        assert result.total == 5
        assert len(result.results) == 5

    def test_default_limit_is_50(self, db_session, project, service):
        # Create 60 sources
        for i in range(60):
            _create_source_with_chunks(
                db_session, project.id, f"资料{i}", f"资料{i}魔法"
            )

        result = service.search_chunks(project.id, "魔法")

        assert result.total == 50
        assert len(result.results) == 50


# ---------- Result Structure ----------


class TestResultStructure:
    def test_result_contains_all_required_fields(self, db_session, project, service):
        content = "这是关于魔法体系的详细说明文档。"
        source, chunk = _create_source_with_chunks(
            db_session, project.id, "魔法资料", content, source_type="note", credibility="high"
        )

        result = service.search_chunks(project.id, "魔法")

        assert result.total == 1
        chunk_result = result.results[0]

        # Chunk fields
        assert chunk_result.chunk_id == chunk.id
        assert chunk_result.chunk_index == 0
        assert chunk_result.chunk_content == content
        assert chunk_result.matched_snippet == "魔法"

        # Source fields
        assert chunk_result.source_id == source.id
        assert chunk_result.source_title == "魔法资料"
        assert chunk_result.source_type == "note"
        assert chunk_result.source_credibility == "high"

    def test_result_includes_heading(self, db_session, project, service):
        source_id = str(uuid4())
        source = KnowledgeSource(
            id=source_id,
            project_id=project.id,
            title="资料",
            source_type="note",
            source_uri="",
            author=None,
            summary="",
            content="魔法内容",
            tags="",
            status="active",
            credibility="normal",
        )
        db_session.add(source)

        chunk_id = str(uuid4())
        chunk = KnowledgeChunk(
            id=chunk_id,
            project_id=project.id,
            source_id=source_id,
            chunk_index=0,
            heading="魔法章节",
            content="魔法内容",
            token_count=4,
            metadata_json="{}",
        )
        db_session.add(chunk)
        db_session.commit()

        result = service.search_chunks(project.id, "魔法")

        assert result.total == 1
        assert result.results[0].chunk_heading == "魔法章节"
