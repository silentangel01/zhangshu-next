"""Cloud feedback request/response schemas for the local backend sidecar."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CloudAnnouncementItem(BaseModel):
    id: str
    title: str
    body: str
    severity: str
    published_at: str | None = None
    starts_at: str | None = None
    ends_at: str | None = None


class CloudAnnouncementListResponse(BaseModel):
    items: list[CloudAnnouncementItem]
    total: int
    cloud_available: bool = True


class CloudFeedbackSubmitResponse(BaseModel):
    id: str
    status: str
    uploaded_attachments: int = 0
    failed_attachments: int = 0
