"""Authentication request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

EmailCodePurpose = Literal["register", "login", "bind"]
PhoneCodePurpose = Literal["register", "login", "bind"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str = ""
    verification_code: str = Field(default="", min_length=0, max_length=10)


class EmailCheckRequest(BaseModel):
    email: EmailStr


class EmailCheckResponse(BaseModel):
    email: str
    available: bool


class SendEmailCodeRequest(BaseModel):
    email: EmailStr
    purpose: EmailCodePurpose


class SendEmailCodeResponse(BaseModel):
    ok: bool
    expires_in_seconds: int
    cooldown_seconds: int


class EmailCodeLoginRequest(BaseModel):
    email: EmailStr
    verification_code: str = Field(min_length=4, max_length=10)


class PhoneCheckRequest(BaseModel):
    phone_number: str


class PhoneCheckResponse(BaseModel):
    phone_number: str
    available: bool


class SendPhoneCodeRequest(BaseModel):
    phone_number: str
    purpose: PhoneCodePurpose


class PhoneRegisterRequest(BaseModel):
    phone_number: str
    verification_code: str = Field(min_length=4, max_length=10)
    display_name: str = ""


class PhoneCodeLoginRequest(BaseModel):
    phone_number: str
    verification_code: str = Field(min_length=4, max_length=10)


class OAuthStartResponse(BaseModel):
    provider: str
    authorization_url: str
    session_id: str
    poll_token: str
    expires_in_seconds: int


class OAuthPollResponse(BaseModel):
    status: str
    provider: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    user_id: str | None = None
    display_name: str | None = None
    error_message: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str | None = None


class MeResponse(BaseModel):
    id: str
    email: str
    display_name: str
