"""Schemas for admin dashboard API."""

from __future__ import annotations

from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    total_users: int
    active_24h: int
    active_7d: int
    active_30d: int
    today_registrations: int
    total_cloud_projects: int
    total_cloud_backups: int
    total_storage_bytes: int
    open_feedback: int
    urgent_feedback: int


class DailyCount(BaseModel):
    day: str
    count: int


class ActivitySeriesResponse(BaseModel):
    days: int
    daily_active: list[DailyCount]
    daily_registrations: list[DailyCount]
    daily_feedback: list[DailyCount]
    daily_backups: list[DailyCount]


class FeedbackStatsResponse(BaseModel):
    by_status: dict[str, int]
    by_category: dict[str, int]
