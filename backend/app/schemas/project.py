import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


VALID_PROJECT_STATUSES = {"planning", "writing", "paused", "completed", "archived"}

MAX_TAG_LENGTH = 24
MAX_TAG_COUNT = 20


def normalize_tags(raw: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tag in raw:
        trimmed = tag.strip()
        if not trimmed:
            continue
        if len(trimmed) > MAX_TAG_LENGTH:
            trimmed = trimmed[:MAX_TAG_LENGTH]
        if trimmed in seen:
            continue
        seen.add(trimmed)
        result.append(trimmed)
    return result[:MAX_TAG_COUNT]


def encode_tags(tags: list[str]) -> str:
    return json.dumps(tags, ensure_ascii=False)


def decode_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str | None = Field(default=None, max_length=128)
    genre: str | None = Field(default=None, max_length=100)
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: str = Field(default="planning", max_length=32)
    target_word_count: int | None = Field(default=None, ge=0)

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title

    @field_validator("author")
    @classmethod
    def strip_author(cls, value: str | None) -> str | None:
        if value is None:
            return value
        trimmed = value.strip()
        return trimmed or None

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Tags must be a list of strings")
        return normalize_tags([str(item) for item in value])

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_PROJECT_STATUSES:
            raise ValueError(
                f"Status must be one of {sorted(VALID_PROJECT_STATUSES)}"
            )
        return value


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, max_length=128)
    genre: str | None = Field(default=None, max_length=100)
    summary: str | None = None
    tags: list[str] | None = None
    status: str | None = Field(default=None, max_length=32)
    target_word_count: int | None = Field(default=None, ge=0)

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title

    @field_validator("author")
    @classmethod
    def strip_author(cls, value: str | None) -> str | None:
        if value is None:
            return value
        trimmed = value.strip()
        return trimmed or None

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if not isinstance(value, list):
            raise ValueError("Tags must be a list of strings")
        return normalize_tags([str(item) for item in value])

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in VALID_PROJECT_STATUSES:
            raise ValueError(
                f"Status must be one of {sorted(VALID_PROJECT_STATUSES)}"
            )
        return value


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    author: str | None
    genre: str | None
    summary: str | None
    tags: list[str]
    cover_image_path: str | None
    status: str
    target_word_count: int | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return decode_tags(value)
        if isinstance(value, list):
            return [str(item) for item in value]
        return []
