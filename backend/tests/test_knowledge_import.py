"""Tests for the knowledge import service."""

import io
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch
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
    KnowledgeImportLimitError,
    KnowledgeImportProjectNotFoundError,
    KnowledgeImportService,
)
from app.utils.import_parsers import (  # noqa: E402
    KNOWLEDGE_MAX_FILE_COUNT,
    KNOWLEDGE_MAX_FILE_SIZE,
    KNOWLEDGE_MAX_TOTAL_SIZE,
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


# ---------- .doc Tests ----------


class TestDocFormat:
    def test_doc_text_extraction(self, service):
        """Test .doc import with mocked extract_doc_text."""
        fake_doc_content = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1fake doc content"
        files = [
            ("旧文档.doc", fake_doc_content),
            _txt_file("笔记.txt", "笔记内容"),
        ]

        with patch(
            "app.utils.document_text_extractors.extract_doc_text",
            return_value=".doc 提取的文本内容",
        ):
            result = service.preview_import(files)

        assert result["document_count"] == 2
        assert result["can_import"] is True
        doc_document = next(d for d in result["documents"] if d["extension"] == ".doc")
        assert doc_document["title"] == "旧文档"
        assert ".doc 提取的文本内容" in doc_document["content"]

    def test_doc_extraction_failure(self, service):
        """Test that failed .doc extraction is reported properly."""
        files = [
            ("损坏文档.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1corrupted"),
            _txt_file("有效.txt", "有效内容"),
        ]

        def mock_extract_fail(content, filename, failed_files):
            failed_files.append(filename)
            return None

        with patch(
            "app.utils.document_text_extractors.extract_doc_text",
            side_effect=mock_extract_fail,
        ):
            result = service.preview_import(files)

        assert result["document_count"] == 1  # Only the .txt file
        assert "损坏文档.doc" in result["failed_files"]
        doc_warnings = [w for w in result["warnings"] if ".doc" in w]
        assert len(doc_warnings) > 0

    def test_doc_not_in_unsupported(self, service):
        """Test that .doc is no longer listed as unsupported."""
        files = [
            ("旧文档.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
            _txt_file("笔记.txt", "笔记内容"),
        ]

        with patch(
            "app.utils.document_text_extractors.extract_doc_text",
            return_value="提取成功",
        ):
            result = service.preview_import(files)

        assert "旧文档.doc" not in result["unsupported_files"]
        assert result["unsupported_count"] == 0


# ---------- PDF Tests ----------


class TestPdfFormat:
    def test_pdf_text_extraction(self, service):
        """Test PDF import with mocked pypdf extraction."""
        fake_pdf_content = b"%PDF-1.4 fake pdf content"
        files = [
            ("文档.pdf", fake_pdf_content),
            _txt_file("笔记.txt", "笔记内容"),
        ]

        with patch(
            "app.utils.document_text_extractors.extract_pdf_text",
            return_value="PDF 提取的文本内容",
        ):
            result = service.preview_import(files)

        assert result["document_count"] == 2
        assert result["can_import"] is True
        pdf_doc = next(d for d in result["documents"] if d["extension"] == ".pdf")
        assert pdf_doc["title"] == "文档"
        assert "PDF 提取的文本内容" in pdf_doc["content"]

    def test_pdf_extraction_failure(self, service):
        """Test that failed PDF extraction is reported properly."""
        files = [
            ("扫描版.pdf", b"%PDF-1.4 encrypted or scanned"),
            _txt_file("有效.txt", "有效内容"),
        ]

        def mock_extract_fail(content, filename, failed_files):
            failed_files.append(filename)
            return None

        with patch(
            "app.utils.document_text_extractors.extract_pdf_text",
            side_effect=mock_extract_fail,
        ):
            result = service.preview_import(files)

        assert result["document_count"] == 1  # Only the .txt file
        assert "扫描版.pdf" in result["failed_files"]
        # Should have a warning about PDF failure
        pdf_warnings = [w for w in result["warnings"] if "PDF" in w]
        assert len(pdf_warnings) > 0


# ---------- Zip Tests ----------


class TestZipImport:
    def _make_zip(self, entries: dict[str, bytes]) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, content in entries.items():
                zf.writestr(name, content)
        return buf.getvalue()

    def test_zip_with_multiple_txt_files(self, service):
        zip_content = self._make_zip({
            "资料/笔记1.txt": "笔记内容一".encode("utf-8"),
            "资料/笔记2.txt": "笔记内容二".encode("utf-8"),
            "资料/子目录/笔记3.txt": "笔记内容三".encode("utf-8"),
        })
        files = [("资料集.zip", zip_content)]
        result = service.preview_import(files)

        assert result["document_count"] == 3
        assert result["can_import"] is True

    def test_zip_with_mixed_formats(self, service):
        zip_content = self._make_zip({
            "笔记.txt": "文本内容".encode("utf-8"),
            "文档.md": "# Markdown".encode("utf-8"),
            "图片.png": b"\x89PNG",
        })
        files = [("混合.zip", zip_content)]
        result = service.preview_import(files)

        assert result["document_count"] == 2
        assert "图片.png" in result["unsupported_files"]

    def test_zip_path_traversal_rejected(self, service):
        zip_content = self._make_zip({
            "../../../etc/passwd": "malicious content".encode("utf-8"),
            "正常文件.txt": "正常内容".encode("utf-8"),
        })
        files = [("恶意.zip", zip_content)]
        result = service.preview_import(files)

        assert result["document_count"] == 1
        assert "../../../etc/passwd" in result["failed_files"]

    def test_zip_ignores_system_files(self, service):
        zip_content = self._make_zip({
            ".DS_Store": b"macOS metadata",
            "Thumbs.db": b"windows thumbnail cache",
            "__MACOSX/resource": b"resource fork",
            "笔记.txt": "有效内容".encode("utf-8"),
        })
        files = [("带系统文件.zip", zip_content)]
        result = service.preview_import(files)

        assert result["document_count"] == 1
        assert result["document_count"] == 1

    def test_zip_empty_archive(self, service):
        zip_content = self._make_zip({})
        files = [("空压缩包.zip", zip_content)]
        result = service.preview_import(files)

        assert result["document_count"] == 0
        assert result["can_import"] is False

    def test_zip_preserves_relative_paths(self, service):
        zip_content = self._make_zip({
            "文件夹/子文件夹/深层笔记.txt": "深层内容".encode("utf-8"),
        })
        files = [("资料.zip", zip_content)]
        result = service.preview_import(files)

        assert result["document_count"] == 1
        doc = result["documents"][0]
        assert doc["source_uri"] == "文件夹/子文件夹/深层笔记.txt"

    def test_bad_zip_file(self, service):
        files = [("损坏.zip", b"this is not a zip file")]
        result = service.preview_import(files)

        assert result["document_count"] == 0
        assert "损坏.zip" in result["failed_files"]

    def test_zip_with_doc_supported(self, service):
        zip_content = self._make_zip({
            "旧文档.doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
            "新文档.docx": b"PK\x03\x04",
            "笔记.txt": "有效内容".encode("utf-8"),
        })
        files = [("混合文档.zip", zip_content)]

        with patch(
            "app.utils.import_parsers.parse_docx_text",
            return_value="docx 内容",
        ), patch(
            "app.utils.document_text_extractors.extract_doc_text",
            return_value="doc 内容",
        ):
            result = service.preview_import(files)

        assert "旧文档.doc" not in result["unsupported_files"]
        assert result["document_count"] == 3


# ---------- Upload Limit Tests ----------


class TestUploadLimits:
    def test_file_count_limit(self, service):
        files = [
            _txt_file(f"文件{i}.txt", f"内容{i}")
            for i in range(KNOWLEDGE_MAX_FILE_COUNT + 1)
        ]
        with pytest.raises(KnowledgeImportLimitError):
            service.preview_import(files)

    def test_single_file_size_limit(self, service):
        oversized = b"x" * (KNOWLEDGE_MAX_FILE_SIZE + 1)
        files = [("大文件.txt", oversized)]
        with pytest.raises(KnowledgeImportLimitError):
            service.preview_import(files)

    def test_total_size_limit(self, service):
        # Create many files that together exceed the total limit
        chunk_size = KNOWLEDGE_MAX_FILE_SIZE  # Each file at single-file limit
        count = (KNOWLEDGE_MAX_TOTAL_SIZE // chunk_size) + 2
        files = [
            _txt_file(f"文件{i}.txt", "x" * chunk_size)
            for i in range(count)
        ]
        with pytest.raises(KnowledgeImportLimitError):
            service.preview_import(files)


# ---------- Enhanced Preview Fields ----------


class TestEnhancedPreviewFields:
    def test_preview_has_supported_count(self, service):
        files = [
            _txt_file("笔记.txt", "内容"),
            ("不支持.png", b"\x89PNG"),
        ]
        result = service.preview_import(files)

        assert result["supported_count"] == 1
        assert result["unsupported_count"] == 1

    def test_preview_has_total_size(self, service):
        content1 = "内容一"
        content2 = "内容二更长的内容"
        files = [
            _txt_file("文件1.txt", content1),
            _txt_file("文件2.txt", content2),
        ]
        result = service.preview_import(files)

        expected_size = len(content1.encode("utf-8")) + len(content2.encode("utf-8"))
        assert result["total_size"] == expected_size

    def test_document_has_relative_path_and_extension(self, service):
        files = [
            ("文件夹/子目录/笔记.md", "# 标题\n内容".encode("utf-8")),
        ]
        result = service.preview_import(files)

        assert result["document_count"] == 1
        doc = result["documents"][0]
        assert doc["relative_path"] == "文件夹/子目录/笔记.md"
        assert doc["extension"] == ".md"
        assert doc["size"] > 0

    def test_folder_relative_path_in_source_uri(self, db_session, project, service):
        files = [
            ("资料/参考文件.txt", "参考内容".encode("utf-8")),
        ]
        result = service.confirm_import(project.id, files)

        source = db_session.query(KnowledgeSource).filter(
            KnowledgeSource.id == result["imported_sources"][0]["id"]
        ).first()
        assert source.source_uri == "资料/参考文件.txt"
