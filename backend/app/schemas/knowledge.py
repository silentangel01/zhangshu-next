from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


KnowledgeSourceType = Literal["note", "file", "webpage", "book", "quote", "custom"]
KnowledgeSourceStatus = Literal["active", "archived"]
KnowledgeCredibility = Literal["low", "normal", "high"]
KnowledgeLinkTargetType = Literal[
    "project",
    "chapter",
    "character",
    "setting",
    "clue",
    "timeline_event",
    "graph_node",
]
KnowledgeLinkRelationType = Literal[
    "reference",
    "inspiration",
    "evidence",
    "background",
    "related",
]


class KnowledgeSourceBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    source_type: KnowledgeSourceType = "note"
    source_uri: str = ""
    author: str | None = None
    summary: str = ""
    content: str = ""
    tags: str = ""
    status: KnowledgeSourceStatus = "active"
    credibility: KnowledgeCredibility = "normal"

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title


class KnowledgeSourceCreate(KnowledgeSourceBase):
    pass


class KnowledgeSourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    source_type: KnowledgeSourceType | None = None
    source_uri: str | None = None
    author: str | None = None
    summary: str | None = None
    content: str | None = None
    tags: str | None = None
    status: KnowledgeSourceStatus | None = None
    credibility: KnowledgeCredibility | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value
        title = value.strip()
        if not title:
            raise ValueError("标题不能为空")
        return title


class KnowledgeSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    source_type: str
    source_uri: str
    author: str | None
    summary: str
    content: str
    tags: str
    status: str
    credibility: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class KnowledgeSourceList(BaseModel):
    total: int
    items: list[KnowledgeSourceRead]


class KnowledgeChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    source_id: str
    chunk_index: int
    heading: str
    content: str
    token_count: int
    metadata_json: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class KnowledgeLinkCreate(BaseModel):
    chunk_id: str | None = None
    target_type: KnowledgeLinkTargetType
    target_id: str
    relation_type: KnowledgeLinkRelationType = "reference"
    note: str = ""


class KnowledgeLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    source_id: str
    chunk_id: str | None
    target_type: str
    target_id: str
    relation_type: str
    note: str
    created_at: datetime
    deleted_at: datetime | None


class KnowledgeSourceFilters(BaseModel):
    keyword: str | None = None
    source_type: KnowledgeSourceType | None = None
    status: KnowledgeSourceStatus | None = None
    tag: str | None = None
    credibility: KnowledgeCredibility | None = None


# --- Knowledge Import Response Schemas ---


class KnowledgeImportDocumentRead(BaseModel):
    title: str
    content: str
    source_type: str
    source_uri: str
    filename: str
    relative_path: str
    extension: str
    word_count: int
    size: int


class KnowledgeImportPreviewResponse(BaseModel):
    documents: list[KnowledgeImportDocumentRead]
    document_count: int
    supported_count: int
    unsupported_count: int
    total_word_count: int
    total_size: int
    warnings: list[str]
    failed_files: list[str]
    empty_files: list[str]
    unsupported_files: list[str]
    can_import: bool


class KnowledgeImportedSourceRead(BaseModel):
    id: str
    title: str
    source_type: str
    source_uri: str
    chunk_count: int


class KnowledgeImportResultResponse(BaseModel):
    imported_count: int
    imported_sources: list[KnowledgeImportedSourceRead]
    warnings: list[str]
    failed_files: list[str]
    empty_files: list[str]
    unsupported_files: list[str]
