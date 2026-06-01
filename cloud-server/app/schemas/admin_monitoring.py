"""Schemas for admin monitoring API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ModuleResponse(BaseModel):
    """Wrapper for a single monitoring module result."""

    data: dict[str, Any] | None = None
    error: str | None = None
    cached_at: str
    ttl_seconds: int


class MonitoringOverviewResponse(BaseModel):
    """Aggregated response for all monitoring modules."""

    billing: ModuleResponse
    oss: ModuleResponse
    server: ModuleResponse
