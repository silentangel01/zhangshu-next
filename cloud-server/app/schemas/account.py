"""Account management request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class BoundIdentityResponse(BaseModel):
    provider: str
    identifier: str


class ProfileResponse(BaseModel):
    id: str
    email: str | None
    phone_number: str | None = None
    identities: list[BoundIdentityResponse] = []
    display_name: str
    signature: str | None = None
    avatar_url: str | None = None
    avatar_updated_at: datetime | None = None
    password_changed_at: datetime | None = None
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    signature: str | None = None


class BindEmailCodeRequest(BaseModel):
    email: EmailStr


class BindPhoneCodeRequest(BaseModel):
    phone_number: str


class BindEmailRequest(BaseModel):
    email: EmailStr
    verification_code: str = Field(min_length=4, max_length=10)


class BindPhoneRequest(BaseModel):
    phone_number: str
    verification_code: str = Field(min_length=4, max_length=10)


# --- Avatar ---


class AvatarInitRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int


class AvatarInitResponse(BaseModel):
    upload_url: str
    upload_id: str
    expires_at: datetime
    object_key: str


class AvatarCompleteRequest(BaseModel):
    upload_id: str
    object_key: str
    content_type: str
    checksum_sha256: str


class AvatarResponse(BaseModel):
    avatar_url: str | None = None
    avatar_updated_at: datetime | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    message: str


class SessionResponse(BaseModel):
    id: str
    device_id: str | None = None
    device_name: str | None = None
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None = None
    user_agent: str | None = None
    client_ip: str | None = None
    is_current: bool = False
    revoked: bool = False


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int


class RevokeAllResponse(BaseModel):
    revoked_count: int
    message: str


# --- Deletion ---

class DeleteRequestBody(BaseModel):
    password: str


class DeletionRequestResponse(BaseModel):
    request_id: str
    expires_at: datetime
    project_count: int
    backup_count: int
    total_size_bytes: int
    confirmation_text: str


class ConfirmDeleteRequest(BaseModel):
    request_id: str
    confirmation_text: str


class DeleteAccountResponse(BaseModel):
    message: str
    deleted_projects: int
    deleted_backups: int
    oss_failures: int = 0
