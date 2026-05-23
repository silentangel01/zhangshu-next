"""Knowledge base import service.

Supports importing .txt, .md, and .docx files into the knowledge base.
Each file becomes a KnowledgeSource with auto-generated chunks.
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.knowledge_source import KnowledgeSource
from app.repositories.knowledge_repo import KnowledgeRepository
from app.repositories.project_repo import ProjectRepository
from app.services.knowledge_service import KnowledgeService
from app.utils.import_parsers import parse_knowledge_files


class KnowledgeImportProjectNotFoundError(Exception):
    pass


class KnowledgeImportEmptyError(Exception):
    pass


class KnowledgeImportService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = KnowledgeRepository(db)
        self.project_repo = ProjectRepository(db)
        self.knowledge_service = KnowledgeService(db)

    def preview_import(
        self, file_entries: list[tuple[str, bytes]]
    ) -> dict:
        """Parse files and return a preview without persisting anything.

        Returns:
            {
                "documents": [...],
                "document_count": int,
                "total_word_count": int,
                "warnings": [...],
                "failed_files": [...],
                "empty_files": [...],
                "unsupported_files": [...],
                "can_import": bool,
            }
        """
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
        """Parse files and persist them as KnowledgeSource entries.

        Returns:
            {
                "imported_count": int,
                "imported_sources": [{id, title, source_type, chunk_count}],
                "warnings": [...],
                "failed_files": [...],
                "empty_files": [...],
                "unsupported_files": [...],
            }
        """
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
