from datetime import datetime
from typing import Literal

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

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Name must not be empty")
        return name


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

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value

        name = value.strip()
        if not name:
            raise ValueError("Name must not be empty")
        return name


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
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


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
