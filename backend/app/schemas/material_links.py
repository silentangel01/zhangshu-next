from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


TimelineEventCharacterRelationType = Literal[
    "appears",
    "pov",
    "conflict",
    "supports",
    "mentions",
    "causes",
    "affected_by",
    "related",
]
TimelineEventSettingRelationType = Literal[
    "location",
    "object",
    "organization",
    "rule",
    "background",
    "affected_by",
    "related",
]
TimelineEventClueRelationType = Literal[
    "setup",
    "develop",
    "payoff",
    "reveals",
    "causes",
    "related",
]
OutlineCharacterRelationType = Literal[
    "appears",
    "pov",
    "conflict",
    "supports",
    "target",
    "related",
]
OutlineSettingRelationType = Literal[
    "location",
    "object",
    "organization",
    "rule",
    "background",
    "related",
]
OutlineClueRelationType = Literal[
    "setup",
    "develop",
    "payoff",
    "hint",
    "related",
]
OutlineTimelineEventRelationType = Literal[
    "planned_event",
    "actual_event",
    "previous",
    "next",
    "parallel",
    "related",
]


class TimelineEventCharacterLinkCreate(BaseModel):
    character_id: str
    relation_type: TimelineEventCharacterRelationType = "related"
    note: str = ""


class TimelineEventSettingLinkCreate(BaseModel):
    setting_id: str
    relation_type: TimelineEventSettingRelationType = "related"
    note: str = ""


class TimelineEventClueLinkCreate(BaseModel):
    clue_id: str
    relation_type: TimelineEventClueRelationType = "related"
    note: str = ""


class OutlineCharacterLinkCreate(BaseModel):
    character_id: str
    relation_type: OutlineCharacterRelationType = "related"
    note: str = ""


class OutlineSettingLinkCreate(BaseModel):
    setting_id: str
    relation_type: OutlineSettingRelationType = "related"
    note: str = ""


class OutlineClueLinkCreate(BaseModel):
    clue_id: str
    relation_type: OutlineClueRelationType = "related"
    note: str = ""


class OutlineTimelineEventLinkCreate(BaseModel):
    timeline_event_id: str
    relation_type: OutlineTimelineEventRelationType = "related"
    note: str = ""


class TimelineEventCharacterLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    timeline_event_id: str
    character_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime


class TimelineEventSettingLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    timeline_event_id: str
    setting_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime


class TimelineEventClueLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    timeline_event_id: str
    clue_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime


class OutlineCharacterLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    outline_item_id: str
    character_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime


class OutlineSettingLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    outline_item_id: str
    setting_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime


class OutlineClueLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    outline_item_id: str
    clue_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime


class OutlineTimelineEventLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    outline_item_id: str
    timeline_event_id: str
    relation_type: str
    note: str
    created_at: datetime
    updated_at: datetime


class MaterialLinkSummary(BaseModel):
    timeline_event_character_count: int
    timeline_event_setting_count: int
    timeline_event_clue_count: int
    outline_character_count: int
    outline_setting_count: int
    outline_clue_count: int
    outline_timeline_event_count: int
