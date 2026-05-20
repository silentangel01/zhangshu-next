from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.chapter import ChapterRead
from app.schemas.setting import SettingRead


TimelineEventType = Literal["plot", "background", "character", "world", "clue", "conflict", "custom"]
TimelineEventImportance = Literal["low", "normal", "high", "critical"]
TimelineEventStatus = Literal["planned", "happened", "revised", "deprecated"]
TimelineTrackType = Literal["main", "character", "organization", "setting", "clue", "volume", "custom"]
TimelineEdgeType = Literal["cause", "parallel", "clue_payoff", "conflict", "echo", "related", "custom"]
TimelineEdgeLineStyle = Literal["straight", "arc", "dashed", "arrow"]
TimelineEdgeVisibility = Literal["normal", "subtle", "hidden"]


class TimelineTrackBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    track_type: TimelineTrackType = "custom"
    bound_type: str | None = None
    bound_id: str | None = None
    order_index: int = 0
    color: str | None = None
    is_main: bool = False

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title

    @field_validator("order_index")
    @classmethod
    def order_index_must_not_be_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Order index must not be negative")
        return value


class TimelineTrackCreate(TimelineTrackBase):
    pass


class TimelineTrackUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    track_type: TimelineTrackType | None = None
    bound_type: str | None = None
    bound_id: str | None = None
    order_index: int | None = None
    color: str | None = None
    is_main: bool | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title

    @field_validator("order_index")
    @classmethod
    def order_index_must_not_be_negative(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 0:
            raise ValueError("Order index must not be negative")
        return value


class TimelineTrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    description: str
    track_type: str
    bound_type: str | None
    bound_id: str | None
    order_index: int
    color: str | None
    is_main: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class TimelineEdgeBase(BaseModel):
    from_event_id: str
    to_event_id: str
    edge_type: TimelineEdgeType = "related"
    line_style: TimelineEdgeLineStyle = "straight"
    label: str = ""
    note: str = ""
    visibility: TimelineEdgeVisibility = "normal"


class TimelineEdgeCreate(TimelineEdgeBase):
    pass


class TimelineEdgeUpdate(BaseModel):
    from_event_id: str | None = None
    to_event_id: str | None = None
    edge_type: TimelineEdgeType | None = None
    line_style: TimelineEdgeLineStyle | None = None
    label: str | None = None
    note: str | None = None
    visibility: TimelineEdgeVisibility | None = None


class TimelineEdgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    from_event_id: str
    to_event_id: str
    edge_type: str
    line_style: str
    label: str
    note: str
    visibility: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class TimelineEventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    event_type: TimelineEventType = "plot"
    story_date: str | None = None
    story_time: str | None = None
    order_index: int = 0
    position_index: int = 0
    importance: TimelineEventImportance = "normal"
    status: TimelineEventStatus = "planned"
    chapter_id: str | None = None
    location_setting_id: str | None = None
    track_id: str | None = None
    note: str = ""

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title

    @field_validator("order_index", "position_index")
    @classmethod
    def index_must_not_be_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Index must not be negative")
        return value


class TimelineEventCreate(TimelineEventBase):
    pass


class TimelineEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    event_type: TimelineEventType | None = None
    story_date: str | None = None
    story_time: str | None = None
    order_index: int | None = None
    position_index: int | None = None
    importance: TimelineEventImportance | None = None
    status: TimelineEventStatus | None = None
    chapter_id: str | None = None
    location_setting_id: str | None = None
    track_id: str | None = None
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

    @field_validator("order_index", "position_index")
    @classmethod
    def index_must_not_be_negative(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 0:
            raise ValueError("Index must not be negative")
        return value


class TimelineEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    description: str
    event_type: str
    story_date: str | None
    story_time: str | None
    order_index: int
    position_index: int
    importance: str
    status: str
    chapter_id: str | None
    location_setting_id: str | None
    track_id: str | None
    note: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
    chapter: ChapterRead | None = None
    location_setting: SettingRead | None = None
