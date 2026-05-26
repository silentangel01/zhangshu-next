"""Project request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CreateProjectRequest(BaseModel):
    title: str


class ProjectResponse(BaseModel):
    id: str
    title: str
    owner_id: str
    created_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
