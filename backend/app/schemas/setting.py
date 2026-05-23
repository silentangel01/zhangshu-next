from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SettingItemType = Literal[
    "world",
    "location",
    "organization",
    "power_system",
    "history",
    "technology",
    "rule",
    "race",
    "object",
    "character",
    "custom",
]
SettingNodeKind = Literal["folder", "page"]
SettingCanonStatus = Literal["draft", "confirmed", "deprecated", "conflicted"]
SettingImportance = Literal["low", "normal", "high", "critical"]
ChapterSettingRelationType = Literal[
    "referenced",
    "appears",
    "explained",
    "changed",
    "conflict_check",
]


class SettingBase(BaseModel):
    parent_id: str | None = None
    title: str = Field(..., min_length=1, max_length=255)
    item_type: SettingItemType | None = None
    canon_status: SettingCanonStatus = "draft"
    summary: str = ""
    detail: str = ""
    tags: str = ""
    order_index: int = Field(default=0, ge=0)
    importance: SettingImportance = "normal"
    node_kind: SettingNodeKind = "page"
    folder_key: str | None = None
    folder_default_item_type: SettingItemType | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class SettingCreate(SettingBase):
    pass


class SettingUpdate(BaseModel):
    parent_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    item_type: SettingItemType | None = None
    canon_status: SettingCanonStatus | None = None
    summary: str | None = None
    detail: str | None = None
    tags: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    importance: SettingImportance | None = None
    node_kind: SettingNodeKind | None = None
    folder_default_item_type: SettingItemType | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value

        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class SettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    parent_id: str | None
    title: str
    item_type: str
    canon_status: str
    summary: str
    detail: str
    tags: str
    order_index: int
    importance: str
    node_kind: str
    folder_key: str | None
    folder_default_item_type: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class ChapterSettingCreate(BaseModel):
    setting_item_id: str
    relation_type: ChapterSettingRelationType = "referenced"
    note: str = ""


class ChapterSettingUpdate(BaseModel):
    relation_type: ChapterSettingRelationType | None = None
    note: str | None = None


class ChapterSettingRead(BaseModel):
    id: str
    project_id: str
    chapter_id: str
    setting_item_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime
    setting_item: SettingRead
