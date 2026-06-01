"""Schemas for admin role management and high-risk action requests."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdminRiskActionRequest(BaseModel):
    """Base request body for high-risk admin actions (toggle-active, force-logout, delete)."""

    reason: str = Field(
        ..., min_length=1, max_length=500, description="Reason for this action."
    )
    confirm_text: str | None = Field(
        default=None,
        max_length=100,
        description="Optional confirmation text for extra-high-risk actions.",
    )


class AdminRoleUpdateRequest(BaseModel):
    """Request body for changing a user's admin role."""

    admin_role: str | None = Field(
        ...,
        description="New admin role (owner/admin/support/ops/readonly) or null to remove.",
    )
    reason: str = Field(..., min_length=1, max_length=500)
    confirm_text: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description='Must type "确认变更角色" to confirm.',
    )


class AdminPermissionMatrixResponse(BaseModel):
    """Role → permissions mapping."""

    roles: dict[str, list[str]]
    current_user_role: str | None = None
    current_user_permissions: list[str] = []
