"""Tests for the knowledge import service."""

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
from app.services.knowledge_import_service import (  # noqa: E402
    KnowledgeImportEmptyError,
    KnowledgeImportProjectNotFoundError,
    KnowledgeImportService,
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
    return KnowledgeImportService(db_session)


# --- Helper ---


def _txt_file(name: str, content: str) -> tuple[str, bytes]:
    return (name, content.encode("utf-8"))


def _md_file(name: str, content: str) -> tuple[str, bytes]:
    return (name, content.encode("utf-8"))


# ---------- Preview Tests ----------


class TestPreviewImport:
    def test_preview_valid_files(self, service):
        files = [
            _txt_file("笔记.txt", "这是一段笔记内容"),
            _md_file("文档.md", "# 标题\n\n这是 Markdown 内容"),
        ]
        result = service.preview_import(files)

        assert result["document_count"] == 2
        assert result["can_import"] is True
        assert len(result["failed_files"]) == 0
        assert len(result["empty_files"]) == 0

    def test_preview_empty_file(self, service):
        files = [
            _txt_file("空文件.txt", ""),
            _txt_file("有内容.txt", "有内容"),
        ]
        result = service.preview_import(files)

        assert result["document_count"] == 1
        assert "空文件.txt" in result["empty_files"]
        assert len(result["warnings"]) > 0

    def test_preview_unsupported_file(self, service):
        files = [
            ("图片.png", b"\x89PNG"),
            _txt_file("有效.txt", "有效内容"),
        ]
        result = service.preview_import(files)

        assert result["document_count"] == 1
        assert "图片.png" in result["unsupported_files"]

    def test_preview_no_valid_files(self, service):
        files = [
            ("图片.png", b"\x89PNG"),
        ]
        result = service.preview_import(files)

        assert result["document_count"] == 0
        assert result["can_import"] is False

    def test_preview_encoding_detection(self, service):
        # UTF-8 BOM
        content = b"\xef\xbb\xbfUTF-8 BOM content"
        files = [("bom.txt", content)]
        result = service.preview_import(files)

        assert result["document_count"] == 1
        assert len(result["failed_files"]) == 0


# ---------- Confirm Tests ----------


class TestConfirmImport:
    def test_confirm_creates_sources(self, db_session, project, service):
        files = [
            _txt_file("笔记1.txt", "笔记内容一"),
            _txt_file("笔记2.txt", "笔记内容二"),
        ]
        result = service.confirm_import(project.id, files)

        assert result["imported_count"] == 2
        assert len(result["imported_sources"]) == 2

        # Verify in database
        sources = db_session.query(KnowledgeSource).filter(
            KnowledgeSource.project_id == project.id,
            KnowledgeSource.deleted_at.is_(None),
        ).all()
        assert len(sources) == 2
        titles = {s.title for s in sources}
        assert "笔记1" in titles
        assert "笔记2" in titles

    def test_confirm_auto_generates_chunks(self, db_session, project, service):
        content = "段落一。\n\n段落二。\n\n段落三。"
        files = [_txt_file("多段.txt", content)]
        result = service.confirm_import(project.id, files)

        assert result["imported_count"] == 1
        source_info = result["imported_sources"][0]
        assert source_info["chunk_count"] >= 1

        # Verify chunks in database
        chunks = db_session.query(KnowledgeChunk).filter(
            KnowledgeChunk.source_id == source_info["id"],
            KnowledgeChunk.deleted_at.is_(None),
        ).all()
        assert len(chunks) >= 1

    def test_confirm_with_tags_and_credibility(self, db_session, project, service):
        files = [_txt_file("标记.txt", "标记内容")]
        result = service.confirm_import(
            project.id,
            files,
            credibility="high",
            tags="导入,测试",
        )

        assert result["imported_count"] == 1
        source = db_session.query(KnowledgeSource).filter(
            KnowledgeSource.id == result["imported_sources"][0]["id"]
        ).first()
        assert source.credibility == "high"
        assert source.tags == "导入,测试"

    def test_confirm_project_not_found(self, service):
        files = [_txt_file("test.txt", "content")]
        with pytest.raises(KnowledgeImportProjectNotFoundError):
            service.confirm_import(str(uuid4()), files)

    def test_confirm_no_valid_files(self, project, service):
        files = [("图片.png", b"\x89PNG")]
        with pytest.raises(KnowledgeImportEmptyError):
            service.confirm_import(project.id, files)

    def test_confirm_empty_files_skipped(self, db_session, project, service):
        files = [
            _txt_file("空.txt", ""),
            _txt_file("有效.txt", "有效内容"),
        ]
        result = service.confirm_import(project.id, files)

        assert result["imported_count"] == 1
        assert "空.txt" in result["empty_files"]

    def test_confirm_source_uri_is_filename(self, db_session, project, service):
        files = [_txt_file("参考资料.txt", "参考内容")]
        result = service.confirm_import(project.id, files)

        source = db_session.query(KnowledgeSource).filter(
            KnowledgeSource.id == result["imported_sources"][0]["id"]
        ).first()
        assert source.source_uri == "参考资料.txt"

    def test_confirm_large_content_chunked(self, db_session, project, service):
        content = "这是一个用于测试分块功能的较长段落内容。\n\n" * 100
        files = [_txt_file("长文.txt", content)]
        result = service.confirm_import(project.id, files)

        assert result["imported_count"] == 1
        source_info = result["imported_sources"][0]
        assert source_info["chunk_count"] > 1
