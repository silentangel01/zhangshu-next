"""Schemas for admin authentication."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminMeResponse(BaseModel):
    id: str
    email: str
    display_name: str
    admin_role: str | None = None
    permissions: list[str] = []
