"""Schemas for admin user management."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AdminUserListItem(BaseModel):
    id: str
    email: str
    display_name: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login_at: datetime | None = None
    last_seen_at: datetime | None = None
    login_count: int = 0
    cloud_project_count: int = 0
    cloud_backup_count: int = 0
    feedback_count: int = 0


class AdminUserListResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int


class AdminRecentActivity(BaseModel):
    event_type: str
    created_at: datetime


class AdminRecentFeedback(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime


class AdminUserDetail(BaseModel):
    id: str
    email: str
    display_name: str
    signature: str | None = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login_at: datetime | None = None
    last_seen_at: datetime | None = None
    login_count: int = 0
    password_changed_at: datetime | None = None
    cloud_project_count: int = 0
    cloud_backup_count: int = 0
    total_storage_bytes: int = 0
    feedback_count: int = 0
    recent_activity: list[AdminRecentActivity] = []
    recent_feedback: list[AdminRecentFeedback] = []
