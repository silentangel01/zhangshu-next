"""Feedback request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Public feedback schemas
# ------------------------------------------------------------------

class FeedbackAttachmentInit(BaseModel):
    """Client declares what it wants to upload."""
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=120)
    size_bytes: int = Field(..., gt=0)
    checksum_sha256: str | None = Field(default=None, max_length=64)


class FeedbackCreateRequest(BaseModel):
    category: str = Field(..., pattern=r"^(bug|suggestion|data_loss|cloud|ui|other)$")
    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=10, max_length=5000)
    contact_email: str | None = Field(default=None, max_length=255)
    app_version: str | None = Field(default=None, max_length=64)
    platform: str | None = Field(default=None, max_length=64)
    network_mode: str | None = Field(default=None, max_length=32)
    client_diagnostics: dict | None = None
    attachments: list[FeedbackAttachmentInit] = Field(default_factory=list)


class UploadSlot(BaseModel):
    attachment_id: str
    upload_id: str
    upload_url: str
    expires_at: datetime


class FeedbackCreateResponse(BaseModel):
    id: str
    status: str
    upload_slots: list[UploadSlot]


class FeedbackCompleteUpload(BaseModel):
    upload_id: str
    checksum_sha256: str | None = None


class FeedbackCompleteRequest(BaseModel):
    uploads: list[FeedbackCompleteUpload] = Field(default_factory=list)


class FeedbackCompleteResponse(BaseModel):
    id: str
    status: str
    uploaded_attachments: int
    failed_attachments: int


class ClientFeedbackItem(BaseModel):
    """Public-facing feedback summary (no admin internals)."""
    id: str
    category: str
    title: str
    description: str
    status: str
    priority: str | None = None
    attachment_count: int = 0
    reply_count: int = 0
    created_at: datetime
    updated_at: datetime


class ClientFeedbackListResponse(BaseModel):
    items: list[ClientFeedbackItem]
    total: int


# ------------------------------------------------------------------
# Admin feedback schemas
# ------------------------------------------------------------------

class AdminFeedbackAttachmentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    status: str
    created_at: datetime
    uploaded_at: datetime | None = None


class AdminFeedbackResponse(BaseModel):
    id: str
    user_id: str | None = None
    contact_email: str | None = None
    category: str
    title: str
    description: str
    status: str
    priority: str | None = None
    app_version: str | None = None
    platform: str | None = None
    network_mode: str | None = None
    client_diagnostics: dict | None = None
    attachment_count: int
    total_size_bytes: int
    admin_note: str | None = None
    reply_count: int = 0
    attachments: list[AdminFeedbackAttachmentResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AdminFeedbackListResponse(BaseModel):
    items: list[AdminFeedbackResponse]
    total: int


class AdminFeedbackUpdateRequest(BaseModel):
    status: str | None = Field(
        default=None,
        pattern=r"^(open|triaged|in_progress|closed|spam)$",
    )
    priority: str | None = Field(
        default=None,
        pattern=r"^(low|normal|high|urgent)$",
    )
    admin_note: str | None = None


class AdminDownloadUrlResponse(BaseModel):
    download_url: str
    expires_at: datetime


# ------------------------------------------------------------------
# Feedback reply schemas
# ------------------------------------------------------------------

class FeedbackReplyResponse(BaseModel):
    id: str
    ticket_id: str
    author_type: str
    author_display_name: str | None = None
    content: str
    created_at: datetime


class AdminFeedbackReplyCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class AdminFeedbackReplyListResponse(BaseModel):
    items: list[FeedbackReplyResponse]
    total: int
