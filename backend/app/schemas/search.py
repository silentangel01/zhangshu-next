from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


SearchEntityType = Literal[
    "chapter", "setting", "character", "clue", "outline", "knowledge", "timeline", "graph"
]

SearchMode = Literal["fts5", "like"]

# Legacy alias for backward compatibility
MatchedField = Literal["title", "content"]


class ProjectSearchResult(BaseModel):
    entity_type: SearchEntityType
    entity_id: str
    title: str
    subtitle: str | None = None
    matched_field: str | None = None
    snippet: str
    score: float = 0.0
    updated_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class ProjectSearchResponse(BaseModel):
    query: str
    mode: SearchMode = "fts5"
    tokenizer: str = "trigram"
    total: int = 0
    limit: int = 50
    offset: int = 0
    results: list[ProjectSearchResult]


# Legacy schema (kept for type compatibility during migration)
class ChapterSearchResult(BaseModel):
    chapter_id: str
    chapter_title: str
    volume_title: str | None
    matched_field: MatchedField
    snippet: str
    updated_at: datetime


class RebuildSearchIndexResponse(BaseModel):
    project_id: str
    indexed_count: int
    message: str
