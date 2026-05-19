from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


ChapterVersionSource = Literal["manual", "autosave", "restore", "before_restore"]


class CreateChapterVersionRequest(BaseModel):
    source: ChapterVersionSource = "manual"
    note: str | None = None


class ChapterVersionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chapter_id: str
    project_id: str
    title: str
    word_count: int
    source: str
    note: str | None
    created_at: datetime


class ChapterVersionDetail(ChapterVersionListItem):
    content: str
