from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


OutlineItemType = Literal[
    "book_outline",
    "volume_outline",
    "chapter_outline",
    "scene",
    "plot_point",
    "note",
]
OutlineStatus = Literal["planned", "writing", "done", "abandoned"]
OutlineImportance = Literal["normal", "important", "critical"]


class OutlineItemCreate(BaseModel):
    parent_id: str | None = None
    volume_id: str | None = None
    chapter_id: str | None = None
    title: str = Field(..., min_length=1, max_length=255)
    content: str = ""
    item_type: OutlineItemType
    status: OutlineStatus = "planned"
    order_index: int = Field(default=0, ge=0)
    importance: OutlineImportance = "normal"

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class OutlineItemUpdate(BaseModel):
    parent_id: str | None = None
    volume_id: str | None = None
    chapter_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = None
    item_type: OutlineItemType | None = None
    status: OutlineStatus | None = None
    order_index: int | None = Field(default=None, ge=0)
    importance: OutlineImportance | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value

        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class OutlineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    parent_id: str | None
    volume_id: str | None
    chapter_id: str | None
    title: str
    content: str
    item_type: str
    status: str
    order_index: int
    importance: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class OutlineReorderItem(BaseModel):
    outline_id: str
    parent_id: str | None = None
    order_index: int = Field(..., ge=0)


class OutlineReorderRequest(BaseModel):
    items: list[OutlineReorderItem]


class OutlineReorderResponse(BaseModel):
    updated_count: int
