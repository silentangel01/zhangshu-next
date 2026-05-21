from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ReviewScope = Literal["chapter", "volume", "project"]


class ProhibitedTermCreate(BaseModel):
    term: str = Field(..., min_length=1, max_length=255)
    severity: str = Field(default="medium", max_length=32)
    suggestion: str = ""
    enabled: bool = True

    @field_validator("term")
    @classmethod
    def term_must_not_be_empty(cls, value: str) -> str:
        term = value.strip()
        if not term:
            raise ValueError("Term must not be empty")
        return term


class ProhibitedTermUpdate(BaseModel):
    term: str | None = Field(default=None, min_length=1, max_length=255)
    severity: str | None = Field(default=None, max_length=32)
    suggestion: str | None = None
    enabled: bool | None = None

    @field_validator("term")
    @classmethod
    def term_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value
        term = value.strip()
        if not term:
            raise ValueError("Term must not be empty")
        return term


class ProhibitedTermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    term: str
    severity: str
    suggestion: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ReviewCheckRequest(BaseModel):
    scope: ReviewScope
    chapter_id: str | None = None
    volume_id: str | None = None

    @model_validator(mode="after")
    def validate_scope_target(self):
        if self.scope == "chapter" and not self.chapter_id:
            raise ValueError("chapter_id is required for chapter check")
        if self.scope == "volume" and not self.volume_id:
            raise ValueError("volume_id is required for volume check")
        return self


class CheckResultRead(BaseModel):
    id: str
    project_id: str
    chapter_id: str
    chapter_title: str | None = None
    volume_title: str | None = None
    rule_type: str
    matched_text: str
    severity: str
    position_start: int
    position_end: int
    suggestion: str
    created_at: datetime


class ReviewCheckResponse(BaseModel):
    total: int
    results: list[CheckResultRead]
