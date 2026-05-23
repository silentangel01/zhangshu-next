"""Tests for the knowledge service."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.knowledge_source import KnowledgeSource  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from app.models.knowledge_link import KnowledgeLink  # noqa: E402
from app.schemas.knowledge import (  # noqa: E402
    KnowledgeLinkCreate,
    KnowledgeSourceCreate,
    KnowledgeSourceUpdate,
)
from app.services.knowledge_service import (  # noqa: E402
    KnowledgeChunkNotFoundError,
    KnowledgeLinkNotFoundError,
    KnowledgeProjectNotFoundError,
    KnowledgeService,
    KnowledgeSourceNotFoundError,
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
    return KnowledgeService(db_session)


# ---------- Project Not Found ----------


class TestProjectNotFound:
    def test_list_raises_when_project_missing(self, db_session, service):
        with pytest.raises(KnowledgeProjectNotFoundError):
            service.list_sources(str(uuid4()))

    def test_create_raises_when_project_missing(self, db_session, service):
        with pytest.raises(KnowledgeProjectNotFoundError):
            service.create_source(
                str(uuid4()),
                KnowledgeSourceCreate(title="Test"),
            )


# ---------- Source CRUD ----------


class TestCreateSource:
    def test_create_basic_source(self, db_session, project, service):
        data = KnowledgeSourceCreate(
            title="参考资料 A",
            source_type="book",
            content="这是一段很长的正文内容，用于测试自动分块功能。" * 50,
            tags="参考,测试",
        )
        source = service.create_source(project.id, data)

        assert source.id
        assert source.project_id == project.id
        assert source.title == "参考资料 A"
        assert source.source_type == "book"
        assert source.status == "active"
        assert source.credibility == "normal"
        assert source.version == 1

    def test_create_auto_generates_chunks(self, db_session, project, service):
        content = "段落一。\n\n段落二。\n\n段落三。"
        data = KnowledgeSourceCreate(title="分块测试", content=content)
        source = service.create_source(project.id, data)

        chunks = service.list_chunks(source.id)
        assert len(chunks) >= 1

    def test_create_empty_content_no_chunks(self, db_session, project, service):
        data = KnowledgeSourceCreate(title="空正文", content="")
        source = service.create_source(project.id, data)

        chunks = service.list_chunks(source.id)
        assert len(chunks) == 0


class TestUpdateSource:
    def test_update_title(self, db_session, project, service):
        source = service.create_source(
            project.id, KnowledgeSourceCreate(title="原标题")
        )
        updated = service.update_source(source.id, KnowledgeSourceUpdate(title="新标题"))

        assert updated.title == "新标题"
        assert updated.version == 2

    def test_update_content_triggers_rechunk(self, db_session, project, service):
        source = service.create_source(
            project.id,
            KnowledgeSourceCreate(title="分块", content="初始内容"),
        )
        old_chunks = service.list_chunks(source.id)

        new_content = "完全不同的正文。\n\n" * 30
        service.update_source(source.id, KnowledgeSourceUpdate(content=new_content))
        new_chunks = service.list_chunks(source.id)

        # Chunks should be regenerated (different count or content)
        assert len(new_chunks) >= 1


class TestDeleteSource:
    def test_soft_delete(self, db_session, project, service):
        source = service.create_source(
            project.id, KnowledgeSourceCreate(title="待删除")
        )
        deleted = service.delete_source(source.id)

        assert deleted.deleted_at is not None

        with pytest.raises(KnowledgeSourceNotFoundError):
            service.get_source(source.id)


# ---------- Search / Filter ----------


class TestListAndFilter:
    def test_keyword_search(self, db_session, project, service):
        service.create_source(
            project.id, KnowledgeSourceCreate(title="魔法体系研究", content="关于魔法的研究")
        )
        service.create_source(
            project.id, KnowledgeSourceCreate(title="历史年表", content="朝代更替")
        )

        results = service.list_sources(project.id, keyword="魔法")
        assert len(results) == 1
        assert results[0].title == "魔法体系研究"

    def test_filter_by_source_type(self, db_session, project, service):
        service.create_source(
            project.id,
            KnowledgeSourceCreate(title="笔记", source_type="note"),
        )
        service.create_source(
            project.id,
            KnowledgeSourceCreate(title="书籍", source_type="book"),
        )

        results = service.list_sources(project.id, source_type="book")
        assert len(results) == 1
        assert results[0].source_type == "book"

    def test_filter_by_status(self, db_session, project, service):
        service.create_source(
            project.id,
            KnowledgeSourceCreate(title="活跃", status="active"),
        )
        service.create_source(
            project.id,
            KnowledgeSourceCreate(title="归档", status="archived"),
        )

        results = service.list_sources(project.id, status="archived")
        assert len(results) == 1
        assert results[0].status == "archived"

    def test_filter_by_credibility(self, db_session, project, service):
        service.create_source(
            project.id,
            KnowledgeSourceCreate(title="高可信", credibility="high"),
        )
        service.create_source(
            project.id,
            KnowledgeSourceCreate(title="低可信", credibility="low"),
        )

        results = service.list_sources(project.id, credibility="high")
        assert len(results) == 1
        assert results[0].credibility == "high"

    def test_filter_by_tag(self, db_session, project, service):
        service.create_source(
            project.id,
            KnowledgeSourceCreate(title="有标签", tags="魔法,历史"),
        )
        service.create_source(
            project.id,
            KnowledgeSourceCreate(title="无标签", tags=""),
        )

        results = service.list_sources(project.id, tag="魔法")
        assert len(results) == 1
        assert results[0].title == "有标签"


# ---------- Chunks ----------


class TestChunks:
    def test_rebuild_chunks(self, db_session, project, service):
        source = service.create_source(
            project.id,
            KnowledgeSourceCreate(title="分块", content="原始内容段落"),
        )
        old_chunks = service.list_chunks(source.id)

        rebuilt = service.rebuild_chunks(source.id)
        assert len(rebuilt) >= 1

        # Old chunks should be soft-deleted, new ones created
        for chunk in rebuilt:
            assert chunk.source_id == source.id
            assert chunk.deleted_at is None

    def test_large_content_split_into_chunks(self, db_session, project, service):
        # Create content that exceeds 1200 chars after merging
        content = "这是一个用于测试分块功能的较长段落内容。\n\n" * 100
        source = service.create_source(
            project.id,
            KnowledgeSourceCreate(title="长文", content=content),
        )

        chunks = service.list_chunks(source.id)
        assert len(chunks) > 1

    def test_chunk_index_sequential(self, db_session, project, service):
        content = "段落 A\n\n段落 B\n\n段落 C\n\n段落 D"
        source = service.create_source(
            project.id,
            KnowledgeSourceCreate(title="序号", content=content),
        )

        chunks = service.list_chunks(source.id)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))


# ---------- Links ----------


class TestLinks:
    def test_create_and_list_link(self, db_session, project, service):
        source = service.create_source(
            project.id, KnowledgeSourceCreate(title="关联测试")
        )
        link = service.create_link(
            source.id,
            KnowledgeLinkCreate(
                target_type="chapter",
                target_id=str(uuid4()),
                relation_type="reference",
                note="参考章节",
            ),
        )

        assert link.id
        assert link.source_id == source.id
        assert link.target_type == "chapter"
        assert link.relation_type == "reference"
        assert link.note == "参考章节"

        links = service.list_links(source.id)
        assert len(links) == 1

    def test_delete_link(self, db_session, project, service):
        source = service.create_source(
            project.id, KnowledgeSourceCreate(title="删除关联")
        )
        link = service.create_link(
            source.id,
            KnowledgeLinkCreate(
                target_type="character",
                target_id=str(uuid4()),
            ),
        )

        deleted = service.delete_link(link.id)
        assert deleted.deleted_at is not None

        links = service.list_links(source.id)
        assert len(links) == 0

    def test_delete_missing_link_raises(self, db_session, project, service):
        with pytest.raises(KnowledgeLinkNotFoundError):
            service.delete_link(str(uuid4()))

    def test_link_with_invalid_chunk_raises(self, db_session, project, service):
        source = service.create_source(
            project.id, KnowledgeSourceCreate(title="无效 chunk")
        )
        with pytest.raises(KnowledgeChunkNotFoundError):
            service.create_link(
                source.id,
                KnowledgeLinkCreate(
                    target_type="chapter",
                    target_id=str(uuid4()),
                    chunk_id=str(uuid4()),
                ),
            )


# ---------- Chunking Algorithm ----------


class TestChunkingAlgorithm:
    def test_heading_split(self, db_session, project, service):
        content = "# 第一章\n\n这是第一章的内容。\n\n# 第二章\n\n这是第二章的内容。"
        source = service.create_source(
            project.id,
            KnowledgeSourceCreate(title="标题分块", content=content),
        )

        chunks = service.list_chunks(source.id)
        headings = [c.heading for c in chunks if c.heading]
        assert len(headings) >= 1

    def test_empty_content_no_chunks(self, db_session, project, service):
        source = service.create_source(
            project.id,
            KnowledgeSourceCreate(title="空", content="   "),
        )

        chunks = service.list_chunks(source.id)
        assert len(chunks) == 0
