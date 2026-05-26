from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


VersionEntityType = Literal[
    "chapter", "setting", "character", "clue", "outline", "knowledge_source"
]

VersionSource = Literal["manual", "autosave", "restore", "before_restore"]


class VersionListItem(BaseModel):
    version_ref: str
    entity_type: str
    entity_id: str
    entity_title: str
    source: str
    label: str | None = None
    note: str | None = None
    is_pinned: bool = False
    word_count: int = 0
    created_at: datetime


class VersionListResponse(BaseModel):
    project_id: str
    total: int
    limit: int
    offset: int
    versions: list[VersionListItem]


class VersionDetail(VersionListItem):
    content_text: str = ""
    snapshot_json: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class CreateVersionSnapshotRequest(BaseModel):
    entity_type: VersionEntityType
    entity_id: str
    label: str | None = None
    note: str | None = None


class UpdateVersionRequest(BaseModel):
    label: str | None = None
    note: str | None = None
    is_pinned: bool | None = None


class VersionCompareRequest(BaseModel):
    version_ref_a: str
    version_ref_b: str | None = None  # None = compare with current entity content


class DiffLine(BaseModel):
    tag: Literal["equal", "insert", "delete", "replace"]
    old_text: str = ""
    new_text: str = ""


class VersionCompareResponse(BaseModel):
    version_ref_a: str
    version_ref_b: str | None
    title_a: str
    title_b: str
    diff: list[DiffLine]


class RestoreVersionResponse(BaseModel):
    version_ref: str
    entity_type: str
    entity_id: str
    before_restore_ref: str
    message: str


class CleanupVersionsResponse(BaseModel):
    deleted_count: int
    message: str
