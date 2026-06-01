"""Usage and quota response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class UsageResponse(BaseModel):
    storage_used_bytes: int
    storage_quota_bytes: int
    backup_count: int
    backup_count_quota: int
    backup_init_used_last_hour: int
    backup_init_limit_per_hour: int
    max_backup_size_bytes: int
