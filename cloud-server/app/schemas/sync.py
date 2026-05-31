"""Pydantic schemas for the incremental sync API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SyncAction = Literal["upsert", "delete"]


# ── Push (client → server) ──────────────────────────────────────


class SyncChangeIn(BaseModel):
    """A single entity change sent by the client."""

    entity_type: str = Field(..., min_length=1, max_length=64)
    entity_id: str = Field(..., min_length=1, max_length=36)
    action: SyncAction = "upsert"
    data: dict[str, Any] | None = None
    base_cloud_version: int = Field(default=0, ge=0)
    local_version: int = Field(default=0, ge=0)
    local_updated_at: datetime | None = None
    device_id: str = Field(default="", max_length=128)


class SyncPushRequest(BaseModel):
    """Batch of changes from the client."""

    cursor: int = Field(default=0, ge=0, description="Client's last known change id")
    changes: list[SyncChangeIn] = Field(default_factory=list)


# ── Push response ────────────────────────────────────────────────


class SyncAcceptedChange(BaseModel):
    entity_type: str
    entity_id: str
    cloud_version: int
    change_id: int


class SyncRejectedChange(BaseModel):
    entity_type: str
    entity_id: str
    reason: str


class SyncConflictResponse(BaseModel):
    entity_type: str
    entity_id: str
    cloud_version: int
    cloud_data: dict[str, Any] | None = None
    local_version: int
    winner: str = "cloud"


class SyncPushResponse(BaseModel):
    new_cursor: int
    accepted: list[SyncAcceptedChange] = Field(default_factory=list)
    rejected: list[SyncRejectedChange] = Field(default_factory=list)
    conflicts: list[SyncConflictResponse] = Field(default_factory=list)


# ── Pull (server → client) ──────────────────────────────────────


class SyncChangeOut(BaseModel):
    """A single change returned by pull."""

    model_config = ConfigDict(from_attributes=True)

    change_id: int
    entity_type: str
    entity_id: str
    action: SyncAction
    cloud_version: int
    data: dict[str, Any] | None = None
    device_id: str = ""
    created_at: datetime


class SyncPullResponse(BaseModel):
    new_cursor: int
    changes: list[SyncChangeOut] = Field(default_factory=list)
    has_more: bool = False


# ── Snapshots / Conflicts (read-only) ───────────────────────────


class SyncSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: str
    cloud_version: int
    payload_json: dict[str, Any] | None = None
    source: str
    device_id: str
    created_at: datetime


class SyncConflictListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: str
    winner_payload_json: dict[str, Any] | None = None
    loser_payload_json: dict[str, Any] | None = None
    winner_source: str
    loser_source: str
    resolved: bool
    created_at: datetime
