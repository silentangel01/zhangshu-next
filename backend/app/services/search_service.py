from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.project import Project
from app.models.volume import Volume
from app.schemas.search import ChapterSearchResult, ProjectSearchResponse


class SearchProjectNotFoundError(Exception):
    pass


class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def search_project_chapters(self, project_id: str, query: str) -> ProjectSearchResponse:
        project = self.db.get(Project, project_id)
        if project is None or project.deleted_at is not None:
            raise SearchProjectNotFoundError()

        keyword = query.strip()
        if not keyword:
            return ProjectSearchResponse(query=query, results=[])

        like_pattern = f"%{self._escape_like(keyword)}%"
        rows = self.db.execute(
            select(Chapter, Volume.title)
            .outerjoin(
                Volume,
                and_(Chapter.volume_id == Volume.id, Volume.deleted_at.is_(None)),
            )
            .where(
                Chapter.project_id == project_id,
                Chapter.deleted_at.is_(None),
                or_(
                    Chapter.title.like(like_pattern, escape="\\"),
                    Chapter.content.like(like_pattern, escape="\\"),
                ),
            )
            .order_by(
                Volume.order_index.asc(),
                Chapter.order_index.asc(),
                Chapter.updated_at.desc(),
                Chapter.id.asc(),
            )
        ).all()

        results = []
        for chapter, volume_title in rows:
            title_matches = self._contains_keyword(chapter.title, keyword)
            matched_field = "title" if title_matches else "content"
            source_text = chapter.title if title_matches else chapter.content
            results.append(
                ChapterSearchResult(
                    chapter_id=chapter.id,
                    chapter_title=chapter.title,
                    volume_title=volume_title,
                    matched_field=matched_field,
                    snippet=self._build_snippet(source_text, keyword),
                    updated_at=chapter.updated_at,
                )
            )

        return ProjectSearchResponse(query=keyword, results=results)

    def _escape_like(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _contains_keyword(self, text: str, keyword: str) -> bool:
        return keyword.casefold() in text.casefold()

    def _build_snippet(self, text: str, keyword: str, radius: int = 36) -> str:
        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
        compact_text = " ".join(normalized_text.split())
        if not compact_text:
            return ""

        index = compact_text.casefold().find(keyword.casefold())
        if index < 0:
            return compact_text[: radius * 2] + ("..." if len(compact_text) > radius * 2 else "")

        start = max(index - radius, 0)
        end = min(index + len(keyword) + radius, len(compact_text))
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(compact_text) else ""
        return f"{prefix}{compact_text[start:end]}{suffix}"
