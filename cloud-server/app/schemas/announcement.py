"""Announcement request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AnnouncementResponse(BaseModel):
    id: str
    title: str
    body: str
    severity: str
    published_at: datetime | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class AnnouncementListResponse(BaseModel):
    items: list[AnnouncementResponse]
    total: int


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    body: str = Field(..., min_length=1)
    severity: str = Field(default="info", pattern=r"^(info|success|warning|critical)$")
    audience: str = Field(default="all")
    platform: str | None = None
    min_app_version: str | None = None
    max_app_version: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class AnnouncementUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = Field(default=None, min_length=1)
    severity: str | None = Field(default=None, pattern=r"^(info|success|warning|critical)$")
    platform: str | None = None
    min_app_version: str | None = None
    max_app_version: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class AdminAnnouncementResponse(AnnouncementResponse):
    status: str
    audience: str
    platform: str | None = None
    min_app_version: str | None = None
    max_app_version: str | None = None
    created_by_id: str | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class AdminAnnouncementListResponse(BaseModel):
    items: list[AdminAnnouncementResponse]
    total: int
