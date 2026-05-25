from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.project import Project
from app.models.volume import Volume
from app.schemas.export import ExportFormat, ExportScope, ManuscriptExportRequest


class ExportNotFoundError(Exception):
    pass


class ExportUnsupportedFormatError(Exception):
    pass


@dataclass
class ExportFile:
    filename: str
    media_type: str
    content: BytesIO


@dataclass
class ManuscriptChapter:
    title: str
    content: str


@dataclass
class ManuscriptVolume:
    title: str | None
    chapters: list[ManuscriptChapter]


@dataclass
class ManuscriptDocument:
    project_title: str
    volumes: list[ManuscriptVolume]


class ExportService:
    def __init__(self, db: Session):
        self.db = db

    def export_manuscript(
        self,
        project_id: str,
        request: ManuscriptExportRequest,
    ) -> ExportFile:
        project = self._get_project(project_id)
        document = self._build_document(project, request)

        if request.format == ExportFormat.docx:
            from app.infrastructure.docx_exporter import render_manuscript_docx

            raw = render_manuscript_docx(document)
            content = BytesIO(raw)
            content.seek(0)
            media_type = (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            extension = "docx"
        else:
            text = (
                self._render_txt(document)
                if request.format == ExportFormat.txt
                else self._render_md(document)
            )
            encoded = text.encode(
                "utf-8-sig" if request.format == ExportFormat.txt else "utf-8"
            )
            content = BytesIO(encoded)
            content.seek(0)
            media_type = (
                "text/plain; charset=utf-8"
                if request.format == ExportFormat.txt
                else "text/markdown; charset=utf-8"
            )
            extension = request.format.value

        return ExportFile(
            filename=f"{self._safe_filename(project.title)}_{request.scope.value}.{extension}",
            media_type=media_type,
            content=content,
        )

    def _get_project(self, project_id: str) -> Project:
        project = self.db.get(Project, project_id)
        if project is None or project.deleted_at is not None:
            raise ExportNotFoundError()
        return project

    def _build_document(
        self,
        project: Project,
        request: ManuscriptExportRequest,
    ) -> ManuscriptDocument:
        if request.scope == ExportScope.chapter:
            chapter = self._get_chapter(project.id, request.chapter_id or "")
            volume = self._get_volume(project.id, chapter.volume_id) if chapter.volume_id else None
            return ManuscriptDocument(
                project_title=project.title,
                volumes=[
                    ManuscriptVolume(
                        title=volume.title if volume else None,
                        chapters=[ManuscriptChapter(title=chapter.title, content=chapter.content)],
                    )
                ],
            )

        if request.scope == ExportScope.volume:
            volume = self._get_volume(project.id, request.volume_id or "")
            chapters = self._list_chapters(project.id, volume.id)
            return ManuscriptDocument(
                project_title=project.title,
                volumes=[
                    ManuscriptVolume(
                        title=volume.title,
                        chapters=[
                            ManuscriptChapter(title=chapter.title, content=chapter.content)
                            for chapter in chapters
                        ],
                    )
                ],
            )

        volumes = self._list_volumes(project.id)
        document_volumes = [
            ManuscriptVolume(
                title=volume.title,
                chapters=[
                    ManuscriptChapter(title=chapter.title, content=chapter.content)
                    for chapter in self._list_chapters(project.id, volume.id)
                ],
            )
            for volume in volumes
        ]
        loose_chapters = self._list_chapters(project.id, None)
        if loose_chapters:
            document_volumes.append(
                ManuscriptVolume(
                    title=None,
                    chapters=[
                        ManuscriptChapter(title=chapter.title, content=chapter.content)
                        for chapter in loose_chapters
                    ],
                )
            )
        return ManuscriptDocument(project_title=project.title, volumes=document_volumes)

    def _get_volume(self, project_id: str, volume_id: str | None) -> Volume:
        if volume_id is None:
            raise ExportNotFoundError()
        volume = self.db.get(Volume, volume_id)
        if volume is None or volume.project_id != project_id or volume.deleted_at is not None:
            raise ExportNotFoundError()
        return volume

    def _get_chapter(self, project_id: str, chapter_id: str) -> Chapter:
        chapter = self.db.get(Chapter, chapter_id)
        if chapter is None or chapter.project_id != project_id or chapter.deleted_at is not None:
            raise ExportNotFoundError()
        return chapter

    def _list_volumes(self, project_id: str) -> list[Volume]:
        return list(
            self.db.scalars(
                select(Volume)
                .where(Volume.project_id == project_id, Volume.deleted_at.is_(None))
                .order_by(Volume.order_index.asc(), Volume.created_at.asc(), Volume.id.asc())
            ).all()
        )

    def _list_chapters(self, project_id: str, volume_id: str | None) -> list[Chapter]:
        query = select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.deleted_at.is_(None),
        )
        query = query.where(Chapter.volume_id.is_(None)) if volume_id is None else query.where(Chapter.volume_id == volume_id)
        return list(
            self.db.scalars(
                query.order_by(Chapter.order_index.asc(), Chapter.created_at.asc(), Chapter.id.asc())
            ).all()
        )

    def _render_txt(self, document: ManuscriptDocument) -> str:
        parts = [document.project_title]
        for volume in document.volumes:
            if volume.title:
                parts.append(volume.title)
            for chapter in volume.chapters:
                parts.append(chapter.title)
                if chapter.content.strip():
                    parts.append(chapter.content.rstrip())
        return "\n\n".join(parts).rstrip() + "\n"

    def _render_md(self, document: ManuscriptDocument) -> str:
        parts = [f"# {document.project_title}"]
        for volume in document.volumes:
            if volume.title:
                parts.append(f"## {volume.title}")
            for chapter in volume.chapters:
                parts.append(f"### {chapter.title}")
                if chapter.content.strip():
                    parts.append(chapter.content.rstrip())
        return "\n\n".join(parts).rstrip() + "\n"

    def _safe_filename(self, value: str) -> str:
        filename = "".join(
            char if char.isascii() and (char.isalnum() or char in ("-", "_")) else "_"
            for char in value.strip()
        ).strip("_")
        return filename or "manuscript"
