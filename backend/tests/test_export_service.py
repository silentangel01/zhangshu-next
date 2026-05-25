"""Tests for DOCX manuscript export."""

import sys
import zipfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.database import Base  # noqa: E402
from app.models.chapter import Chapter  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.volume import Volume  # noqa: E402
from app.schemas.export import ExportFormat, ExportScope, ManuscriptExportRequest  # noqa: E402
from app.services.export_service import ExportService  # noqa: E402


DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_project_with_data(db_session):
    project_id = str(uuid4())
    volume_id = str(uuid4())
    chapter_id = str(uuid4())

    project = Project(id=project_id, title="测试小说")
    db_session.add(project)

    volume = Volume(id=volume_id, project_id=project_id, title="第一卷", order_index=0)
    db_session.add(volume)

    chapter = Chapter(
        id=chapter_id,
        project_id=project_id,
        volume_id=volume_id,
        title="第一章 开端",
        content="这是第一章的正文内容。\n第二段正文。",
        order_index=0,
    )
    db_session.add(chapter)
    db_session.commit()

    return project_id, volume_id, chapter_id


class TestDocxExport:
    def test_docx_export_project(self, db_session):
        project_id, _, _ = _make_project_with_data(db_session)
        service = ExportService(db_session)

        request = ManuscriptExportRequest(
            scope=ExportScope.project,
            format=ExportFormat.docx,
        )
        result = service.export_manuscript(project_id, request)

        assert result.filename.endswith(".docx")
        assert result.media_type == DOCX_MIME

        raw = result.content.getvalue()
        assert zipfile.is_zipfile(BytesIO(raw))

        with zipfile.ZipFile(BytesIO(raw)) as zf:
            assert "word/document.xml" in zf.namelist()
            doc_xml = zf.read("word/document.xml").decode("utf-8")
            assert "测试小说" in doc_xml
            assert "第一卷" in doc_xml
            assert "第一章 开端" in doc_xml
            assert "这是第一章的正文内容" in doc_xml

    def test_docx_export_volume(self, db_session):
        project_id, volume_id, _ = _make_project_with_data(db_session)
        service = ExportService(db_session)

        request = ManuscriptExportRequest(
            scope=ExportScope.volume,
            volume_id=volume_id,
            format=ExportFormat.docx,
        )
        result = service.export_manuscript(project_id, request)

        assert result.filename.endswith(".docx")
        assert result.media_type == DOCX_MIME

    def test_docx_export_chapter(self, db_session):
        project_id, _, chapter_id = _make_project_with_data(db_session)
        service = ExportService(db_session)

        request = ManuscriptExportRequest(
            scope=ExportScope.chapter,
            chapter_id=chapter_id,
            format=ExportFormat.docx,
        )
        result = service.export_manuscript(project_id, request)

        assert result.filename.endswith(".docx")
        assert result.media_type == DOCX_MIME

    def test_txt_export_still_works(self, db_session):
        project_id, _, _ = _make_project_with_data(db_session)
        service = ExportService(db_session)

        request = ManuscriptExportRequest(
            scope=ExportScope.project,
            format=ExportFormat.txt,
        )
        result = service.export_manuscript(project_id, request)

        assert result.filename.endswith(".txt")
        text = result.content.getvalue().decode("utf-8-sig")
        assert "测试小说" in text
        assert "第一章 开端" in text

    def test_md_export_still_works(self, db_session):
        project_id, _, _ = _make_project_with_data(db_session)
        service = ExportService(db_session)

        request = ManuscriptExportRequest(
            scope=ExportScope.project,
            format=ExportFormat.md,
        )
        result = service.export_manuscript(project_id, request)

        assert result.filename.endswith(".md")
        text = result.content.getvalue().decode("utf-8")
        assert "# 测试小说" in text
        assert "### 第一章 开端" in text
