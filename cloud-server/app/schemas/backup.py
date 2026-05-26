"""Backup request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class InitBackupRequest(BaseModel):
    filename: str
    size_bytes: int


class InitBackupResponse(BaseModel):
    upload_url: str
    upload_id: str


class CompleteBackupRequest(BaseModel):
    upload_id: str
    checksum_sha256: str


class CompleteBackupResponse(BaseModel):
    id: str
    object_key: str


class BackupResponse(BaseModel):
    id: str
    filename: str
    size_bytes: int
    checksum_sha256: str | None = None
    status: str
    created_at: datetime
    uploaded_at: datetime | None = None


class BackupListResponse(BaseModel):
    items: list[BackupResponse]
    total: int


class DownloadUrlResponse(BaseModel):
    download_url: str
