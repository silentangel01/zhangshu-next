import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


CharacterRole = Literal[
    "protagonist",
    "deuteragonist",
    "antagonist",
    "supporting",
    "minor",
    "unknown",
]
CharacterImportance = Literal["low", "normal", "high", "critical"]
CharacterStatus = Literal["active", "inactive", "dead", "missing", "unknown"]
ChapterCharacterRelationType = Literal["appears", "mentioned", "pov", "conflict", "supports"]

MAX_PROFILE_SECTIONS = 30
MAX_SECTION_TITLE_LENGTH = 48
MAX_PROFILE_DIMENSIONS = 12
DIMENSION_VALUE_MIN = 0
VALID_DIMENSION_MAXES = {5, 10, 100}
DIMENSION_DEFAULT_MAX = 100


# --- Profile section / dimension models ---


class CharacterProfileSection(BaseModel):
    id: str = ""
    title: str = ""
    content: str = ""
    order: int = 0
    collapsed: bool = False


class CharacterProfileDimension(BaseModel):
    id: str = ""
    name: str = ""
    value: float = 50.0
    max: int = DIMENSION_DEFAULT_MAX
    order: int = 0


# --- Encode / decode / normalize helpers ---


def _to_dict(item: Any) -> dict[str, Any] | None:
    """Convert a Pydantic model or plain dict to a dict, or None if invalid."""
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return None


def normalize_profile_sections(raw: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        d = _to_dict(item)
        if d is None:
            continue
        section_id = str(d.get("id", "") or "").strip()
        title = str(d.get("title", "") or "").strip()
        if not title:
            title = "未命名资料"
        if len(title) > MAX_SECTION_TITLE_LENGTH:
            title = title[:MAX_SECTION_TITLE_LENGTH]
        content = str(d.get("content", "") or "")
        collapsed = bool(d.get("collapsed", False))
        result.append({
            "id": section_id,
            "title": title,
            "content": content,
            "order": idx,
            "collapsed": collapsed,
        })
        if len(result) >= MAX_PROFILE_SECTIONS:
            break
    return result


def encode_profile_sections(sections: list[Any]) -> str:
    if isinstance(sections, str):
        return sections
    normalized = normalize_profile_sections(sections if isinstance(sections, list) else [])
    return json.dumps(normalized, ensure_ascii=False)


def decode_profile_sections(raw: str | list | None) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return normalize_profile_sections(raw)
    if not raw or not isinstance(raw, str):
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return normalize_profile_sections(parsed)
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def normalize_profile_dimensions(raw: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        d = _to_dict(item)
        if d is None:
            continue
        dim_id = str(d.get("id", "") or "").strip()
        name = str(d.get("name", "") or "").strip()
        if not name:
            name = "维度"
        try:
            dim_max = int(d.get("max", DIMENSION_DEFAULT_MAX))
        except (TypeError, ValueError):
            dim_max = DIMENSION_DEFAULT_MAX
        if dim_max not in VALID_DIMENSION_MAXES:
            dim_max = DIMENSION_DEFAULT_MAX
        try:
            value = float(d.get("value", dim_max / 2))
        except (TypeError, ValueError):
            value = float(dim_max / 2)
        # Clamp value to [0, dim_max]
        value = max(float(DIMENSION_VALUE_MIN), min(float(dim_max), value))
        # Round to 1 decimal to avoid floating-point noise
        value = round(value, 1)
        result.append({
            "id": dim_id,
            "name": name,
            "value": value,
            "max": dim_max,
            "order": idx,
        })
        if len(result) >= MAX_PROFILE_DIMENSIONS:
            break
    return result


def encode_profile_dimensions(dimensions: list[Any]) -> str:
    if isinstance(dimensions, str):
        return dimensions
    normalized = normalize_profile_dimensions(dimensions if isinstance(dimensions, list) else [])
    return json.dumps(normalized, ensure_ascii=False)


def decode_profile_dimensions(raw: str | list | None) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return normalize_profile_dimensions(raw)
    if not raw or not isinstance(raw, str):
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return normalize_profile_dimensions(parsed)
    except (json.JSONDecodeError, TypeError):
        pass
    return []


class CharacterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: CharacterRole = "supporting"
    importance: CharacterImportance = "normal"
    status: CharacterStatus = "active"
    faction: str | None = None
    summary: str = ""
    biography: str = ""
    appearance: str = ""
    personality: str = ""
    background: str = ""
    ability: str = ""
    motivation: str = ""
    secret: str = ""
    arc: str = ""
    notes: str = ""
    profile_sections: list[CharacterProfileSection] = Field(default_factory=list)
    profile_dimensions: list[CharacterProfileDimension] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Name must not be empty")
        return name

    @field_validator("profile_sections", mode="before")
    @classmethod
    def validate_profile_sections(cls, value: Any) -> list[dict[str, Any]]:
        if isinstance(value, str):
            return decode_profile_sections(value)
        if isinstance(value, list):
            return normalize_profile_sections(value)
        return []

    @field_validator("profile_dimensions", mode="before")
    @classmethod
    def validate_profile_dimensions(cls, value: Any) -> list[dict[str, Any]]:
        if isinstance(value, str):
            return decode_profile_dimensions(value)
        if isinstance(value, list):
            return normalize_profile_dimensions(value)
        return []


class CharacterCreate(CharacterBase):
    pass


class CharacterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: CharacterRole | None = None
    importance: CharacterImportance | None = None
    status: CharacterStatus | None = None
    faction: str | None = None
    summary: str | None = None
    biography: str | None = None
    appearance: str | None = None
    personality: str | None = None
    background: str | None = None
    ability: str | None = None
    motivation: str | None = None
    secret: str | None = None
    arc: str | None = None
    notes: str | None = None
    profile_sections: list[CharacterProfileSection] | None = None
    profile_dimensions: list[CharacterProfileDimension] | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value

        name = value.strip()
        if not name:
            raise ValueError("Name must not be empty")
        return name

    @field_validator("profile_sections", mode="before")
    @classmethod
    def validate_profile_sections(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, str):
            return decode_profile_sections(value)
        if isinstance(value, list):
            return normalize_profile_sections(value)
        return []

    @field_validator("profile_dimensions", mode="before")
    @classmethod
    def validate_profile_dimensions(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, str):
            return decode_profile_dimensions(value)
        if isinstance(value, list):
            return normalize_profile_dimensions(value)
        return []


class CharacterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    role: str
    importance: str
    status: str
    faction: str | None
    summary: str
    biography: str
    appearance: str
    personality: str
    background: str
    ability: str
    motivation: str
    secret: str
    arc: str
    notes: str
    profile_sections: list[CharacterProfileSection]
    profile_dimensions: list[CharacterProfileDimension]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int

    @field_validator("profile_sections", mode="before")
    @classmethod
    def parse_profile_sections(cls, value: object) -> list[dict[str, Any]]:
        if isinstance(value, str):
            return decode_profile_sections(value)
        if isinstance(value, list):
            return normalize_profile_sections(value)
        return []

    @field_validator("profile_dimensions", mode="before")
    @classmethod
    def parse_profile_dimensions(cls, value: object) -> list[dict[str, Any]]:
        if isinstance(value, str):
            return decode_profile_dimensions(value)
        if isinstance(value, list):
            return normalize_profile_dimensions(value)
        return []


class ChapterCharacterCreate(BaseModel):
    character_id: str
    relation_type: ChapterCharacterRelationType = "appears"
    note: str = ""


class ChapterCharacterUpdate(BaseModel):
    relation_type: ChapterCharacterRelationType | None = None
    note: str | None = None


class ChapterCharacterRead(BaseModel):
    id: str
    project_id: str
    chapter_id: str
    character_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime
    character: CharacterRead
