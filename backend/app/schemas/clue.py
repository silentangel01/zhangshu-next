from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.character import CharacterRead
from app.schemas.setting import SettingRead


ClueStatus = Literal["planned", "planted", "developing", "resolved", "abandoned"]
ClueVisibility = Literal["hidden", "hinted", "revealed"]
ClueImportance = Literal["low", "normal", "high", "critical"]
ChapterClueRelationType = Literal["setup", "mention", "develop", "payoff", "related"]
ClueCharacterRelationType = Literal["related", "holder", "discoverer", "target", "blocker"]
ClueSettingRelationType = Literal["related", "depends_on", "explains", "conflicts_with"]


class ClueBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    setup_chapter_id: str | None = None
    payoff_chapter_id: str | None = None
    status: ClueStatus = "planned"
    visibility: ClueVisibility = "hidden"
    importance: ClueImportance = "normal"
    payoff_plan: str = ""
    actual_payoff: str = ""
    note: str = ""

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class ClueCreate(ClueBase):
    pass


class ClueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    setup_chapter_id: str | None = None
    payoff_chapter_id: str | None = None
    status: ClueStatus | None = None
    visibility: ClueVisibility | None = None
    importance: ClueImportance | None = None
    payoff_plan: str | None = None
    actual_payoff: str | None = None
    note: str | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class ClueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    description: str
    setup_chapter_id: str | None
    payoff_chapter_id: str | None
    status: str
    visibility: str
    importance: str
    payoff_plan: str
    actual_payoff: str
    note: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class ChapterClueCreate(BaseModel):
    clue_id: str
    relation_type: ChapterClueRelationType = "related"
    note: str = ""


class ChapterClueUpdate(BaseModel):
    relation_type: ChapterClueRelationType | None = None
    note: str | None = None


class ChapterClueRead(BaseModel):
    id: str
    project_id: str
    chapter_id: str
    clue_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime
    clue: ClueRead


class ClueCharacterCreate(BaseModel):
    character_id: str
    relation_type: ClueCharacterRelationType = "related"
    note: str = ""


class ClueCharacterUpdate(BaseModel):
    relation_type: ClueCharacterRelationType | None = None
    note: str | None = None


class ClueCharacterRead(BaseModel):
    id: str
    project_id: str
    clue_id: str
    character_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime
    character: CharacterRead


class ClueSettingCreate(BaseModel):
    setting_item_id: str
    relation_type: ClueSettingRelationType = "related"
    note: str = ""


class ClueSettingUpdate(BaseModel):
    relation_type: ClueSettingRelationType | None = None
    note: str | None = None


class ClueSettingRead(BaseModel):
    id: str
    project_id: str
    clue_id: str
    setting_item_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime
    setting: SettingRead
