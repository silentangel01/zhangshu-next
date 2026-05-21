from datetime import datetime
from typing import Literal

from pydantic import BaseModel


MatchedField = Literal["title", "content"]


class ChapterSearchResult(BaseModel):
    chapter_id: str
    chapter_title: str
    volume_title: str | None
    matched_field: MatchedField
    snippet: str
    updated_at: datetime


class ProjectSearchResponse(BaseModel):
    query: str
    results: list[ChapterSearchResult]
