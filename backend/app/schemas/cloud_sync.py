"""Pydantic schemas for local cloud sync API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CloudSyncStatusResponse(BaseModel):
    """Response for GET /api/projects/{project_id}/cloud/sync/status."""

    model_config = ConfigDict(from_attributes=True)

    cloud_logged_in: bool
    cloud_enabled: bool
    pending_count: int
    last_cursor: int
    last_sync_at: datetime | None = None
    last_error: str | None = None
    status: str
    auto_sync_enabled: bool
    cloud_project_id: str | None = None
    device_id: str = ""


class CloudSyncRunRequest(BaseModel):
    """Request body for POST /api/projects/{project_id}/cloud/sync/run."""

    force: bool = False


class CloudSyncRunResult(BaseModel):
    """Response for POST /api/projects/{project_id}/cloud/sync/run."""

    pushed: int
    pulled: int
    new_cursor: int
    conflicts: int
    errors: list[str]
    duration_ms: int


class CloudSyncSnapshotItem(BaseModel):
    """A single cloud sync snapshot."""

    model_config = ConfigDict(from_attributes=True)

    entity_type: str
    entity_id: str
    cloud_version: int
    payload_json: str
    source: str
    device_id: str
    created_at: datetime


class CloudSyncConflictItem(BaseModel):
    """A single cloud sync conflict."""

    model_config = ConfigDict(from_attributes=True)

    entity_type: str
    entity_id: str
    winner_payload_json: str
    loser_payload_json: str
    winner_source: str
    loser_source: str
    winner_device_id: str
    loser_device_id: str
    resolved: bool
    created_at: datetime


class CloudRemoteProject(BaseModel):
    """A remote cloud project available for import."""

    id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None
    linked_locally: bool = False
    local_project_id: str | None = None


class CloudProjectImportRequest(BaseModel):
    """Request body for POST /api/cloud/projects/{cloud_project_id}/import."""

    pass


class CloudProjectImportResult(BaseModel):
    """Response for cloud project import."""

    local_project_id: str
    title: str
    volumes_count: int
    chapters_count: int
    mode: str
    message: str | None = None
