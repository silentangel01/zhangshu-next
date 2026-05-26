"""Pydantic schemas for cloud auth and cloud backup endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── Auth ──────────────────────────────────────────────────────────


class CloudLoginRequest(BaseModel):
    email: str
    password: str


class CloudRegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""


class CloudAccountStatus(BaseModel):
    logged_in: bool
    cloud_available: bool
    email: str | None = None
    display_name: str | None = None


class CloudAuthToken(BaseModel):
    access_token: str
    refresh_token: str = ""
    expires_in: int = 0


# ── Project ───────────────────────────────────────────────────────


class CloudEnableRequest(BaseModel):
    cloud_project_id: str | None = None


class CloudProjectStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cloud_enabled: bool
    cloud_project_id: str | None = None
    provider: str = "zhangshu"
    last_backup_at: datetime | None = None
    last_restore_at: datetime | None = None
    status: str = "active"
    last_error: str | None = None


# ── Backup ────────────────────────────────────────────────────────


class CloudBackupRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    cloud_backup_id: str | None = None
    filename: str
    size_bytes: int | None = None
    checksum_sha256: str | None = None
    encryption_mode: str = "none"
    status: str
    error_message: str | None = None
    created_at: datetime
    uploaded_at: datetime | None = None


class CloudBackupListResponse(BaseModel):
    items: list[CloudBackupRecordResponse]
    total: int


# ── Network ──────────────────────────────────────────────────────────


class CloudNetworkSettingsRequest(BaseModel):
    mode: str  # "auto" | "secure_direct" | "system_proxy" | "compat_no_sni"


class CloudNetworkSettingsResponse(BaseModel):
    mode: str
    last_working_mode: str | None = None
    base_url_configured: bool


class CloudNetworkDiagnosticStep(BaseModel):
    name: str
    ok: bool
    latency_ms: int | None = None
    error_kind: str = ""
    message: str = ""
    suggestion: str = ""


class CloudNetworkDiagnosticReport(BaseModel):
    ok: bool
    recommended_mode: str
    summary: str
    steps: list[CloudNetworkDiagnosticStep]


class CloudDiagnosticRunRequest(BaseModel):
    include_oss: bool = False
