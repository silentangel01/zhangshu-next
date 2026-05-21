from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ChapterStatus = Literal["draft", "writing", "revised", "completed"]
ChapterSaveSource = Literal["manual", "autosave"]


class ChapterBase(BaseModel):
    volume_id: str | None = None
    title: str = Field(..., min_length=1, max_length=255)
    content: str = ""
    order_index: int = Field(default=0, ge=0)
    status: ChapterStatus = "draft"

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class ChapterCreate(ChapterBase):
    pass


class ChapterUpdate(BaseModel):
    volume_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    status: ChapterStatus | None = None
    save_source: ChapterSaveSource = "manual"

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value

        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class ChapterReorderItem(BaseModel):
    chapter_id: str
    volume_id: str | None = None
    order_index: int = Field(default=0, ge=0)


class ChapterReorderRequest(BaseModel):
    items: list[ChapterReorderItem]


class ChapterReorderResponse(BaseModel):
    updated_count: int
    warnings: list[str]


class ChapterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    volume_id: str | None
    title: str
    content: str
    order_index: int
    status: str
    word_count: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
