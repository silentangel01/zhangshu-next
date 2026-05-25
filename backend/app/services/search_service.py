from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.search_index_repo import SearchIndexRepository
from app.schemas.search import (
    ProjectSearchResponse,
    ProjectSearchResult,
    SearchEntityType,
)


# Entity type display labels (Chinese)
ENTITY_TYPE_LABELS: dict[str, str] = {
    "chapter": "正文",
    "setting": "设定",
    "character": "人物",
    "clue": "伏笔",
    "outline": "大纲",
    "knowledge": "知识库",
    "timeline": "时间线",
    "graph": "关系图",
}


class SearchProjectNotFoundError(Exception):
    pass


class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self._repo = SearchIndexRepository(db)

    def search(
        self,
        project_id: str,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ProjectSearchResponse:
        project = self.db.get(Project, project_id)
        if project is None or project.deleted_at is not None:
            raise SearchProjectNotFoundError()

        keyword = query.strip()
        if not keyword:
            return ProjectSearchResponse(
                query=query, results=[], total=0, limit=limit, offset=offset
            )

        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        mode = "fts5" if len(keyword) >= 3 else "like"
        rows, total = self._repo.search(
            project_id=project_id,
            query=keyword,
            entity_types=entity_types,
            limit=limit,
            offset=offset,
        )

        results: list[ProjectSearchResult] = []
        for row in rows:
            meta: dict | None = None
            if row.metadata_json and row.metadata_json != "{}":
                try:
                    meta = json.loads(row.metadata_json)
                except (json.JSONDecodeError, TypeError):
                    meta = None

            updated_at = self._parse_updated_at(row.updated_at)
            subtitle = self._build_subtitle(row.entity_type, meta)

            results.append(
                ProjectSearchResult(
                    entity_type=row.entity_type,  # type: ignore[arg-type]
                    entity_id=row.entity_id,
                    title=row.title,
                    subtitle=subtitle,
                    snippet=self._clean_snippet(row.snippet),
                    score=row.score,
                    updated_at=updated_at,
                    metadata=meta,
                )
            )

        return ProjectSearchResponse(
            query=keyword,
            mode=mode,
            tokenizer="trigram",
            total=total,
            limit=limit,
            offset=offset,
            results=results,
        )

    def rebuild_search_index(self, project_id: str) -> int:
        project = self.db.get(Project, project_id)
        if project is None or project.deleted_at is not None:
            raise SearchProjectNotFoundError()
        return self._repo.rebuild_project(project_id)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _build_subtitle(entity_type: str, meta: dict | None) -> str | None:
        label = ENTITY_TYPE_LABELS.get(entity_type)
        if entity_type == "knowledge" and meta:
            source_id = meta.get("source_id")
            if source_id:
                return f"{label} · 片段"
        return label

    @staticmethod
    def _clean_snippet(snippet: str) -> str:
        """Remove FTS5 highlight markers and normalise whitespace."""
        if not snippet:
            return ""
        return snippet.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")

    @staticmethod
    def _parse_updated_at(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            ts = float(value)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            return None
