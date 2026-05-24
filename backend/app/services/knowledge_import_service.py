"""Knowledge base import service.

Supports importing .txt, .md, .docx, .pdf files and .zip archives into the
knowledge base. Each file becomes a KnowledgeSource with auto-generated chunks.
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.knowledge_source import KnowledgeSource
from app.repositories.knowledge_repo import KnowledgeRepository
from app.repositories.project_repo import ProjectRepository
from app.services.knowledge_service import KnowledgeService
from app.utils.import_parsers import (
    KNOWLEDGE_MAX_FILE_COUNT,
    KNOWLEDGE_MAX_FILE_SIZE,
    KNOWLEDGE_MAX_TOTAL_SIZE,
    parse_knowledge_files,
)


class KnowledgeImportProjectNotFoundError(Exception):
    pass


class KnowledgeImportEmptyError(Exception):
    pass


class KnowledgeImportLimitError(Exception):
    pass


def validate_upload_limits(file_entries: list[tuple[str, bytes]]) -> None:
    """Validate file count and size limits before processing."""
    if len(file_entries) > KNOWLEDGE_MAX_FILE_COUNT:
        raise KnowledgeImportLimitError(
            f"单次最多上传 {KNOWLEDGE_MAX_FILE_COUNT} 个文件，当前选择了 {len(file_entries)} 个。"
        )

    total_size = sum(len(content) for _, content in file_entries)
    if total_size > KNOWLEDGE_MAX_TOTAL_SIZE:
        total_mb = total_size / (1024 * 1024)
        limit_mb = KNOWLEDGE_MAX_TOTAL_SIZE / (1024 * 1024)
        raise KnowledgeImportLimitError(
            f"文件总大小 {total_mb:.1f} MB 超过限制（最大 {limit_mb:.0f} MB）。"
        )

    for filename, content in file_entries:
        if len(content) > KNOWLEDGE_MAX_FILE_SIZE:
            file_mb = len(content) / (1024 * 1024)
            limit_mb = KNOWLEDGE_MAX_FILE_SIZE / (1024 * 1024)
            raise KnowledgeImportLimitError(
                f"文件 {filename} 大小 {file_mb:.1f} MB 超过单文件限制（最大 {limit_mb:.0f} MB）。"
            )


class KnowledgeImportService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = KnowledgeRepository(db)
        self.project_repo = ProjectRepository(db)
        self.knowledge_service = KnowledgeService(db)

    def preview_import(
        self, file_entries: list[tuple[str, bytes]]
    ) -> dict:
        """Parse files and return a preview without persisting anything."""
        validate_upload_limits(file_entries)
        return parse_knowledge_files(file_entries)

    def confirm_import(
        self,
        project_id: str,
        file_entries: list[tuple[str, bytes]],
        *,
        source_type: str = "file",
        credibility: str = "normal",
        tags: str = "",
    ) -> dict:
        """Parse files and persist them as KnowledgeSource entries."""
        validate_upload_limits(file_entries)

        project = self.project_repo.get_active(project_id)
        if project is None:
            raise KnowledgeImportProjectNotFoundError

        preview = parse_knowledge_files(file_entries)
        if not preview["documents"]:
            raise KnowledgeImportEmptyError

        imported_sources = []
        for doc in preview["documents"]:
            source = KnowledgeSource(
                id=str(uuid4()),
                project_id=project_id,
                title=doc["title"],
                source_type=source_type,
                source_uri=doc["source_uri"],
                author=None,
                summary="",
                content=doc["content"],
                tags=tags,
                status="active",
                credibility=credibility,
            )
            source = self.repo.create_source(source)

            # Auto-generate chunks
            chunks = self.knowledge_service.rebuild_chunks(source.id)

            imported_sources.append({
                "id": source.id,
                "title": source.title,
                "source_type": source.source_type,
                "source_uri": source.source_uri,
                "chunk_count": len(chunks),
            })

        return {
            "imported_count": len(imported_sources),
            "imported_sources": imported_sources,
            "warnings": preview["warnings"],
            "failed_files": preview["failed_files"],
            "empty_files": preview["empty_files"],
            "unsupported_files": preview["unsupported_files"],
        }
