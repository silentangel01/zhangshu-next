from typing import Literal

from pydantic import BaseModel


CreativeReminderSeverity = Literal["info", "warning", "critical"]
CreativeReminderType = Literal[
    "important_clue_unresolved",
    "important_character_absent",
    "outline_not_done_for_written_chapter",
    "timeline_event_missing_chapter",
    "graph_node_broken_binding",
    "clue_payoff_without_setup",
    "setting_used_but_draft",
]
CreativeReminderTargetType = Literal[
    "clue",
    "character",
    "outline",
    "timeline_event",
    "graph_node",
    "setting",
    "chapter",
]


class CreativeReminderRead(BaseModel):
    id: str
    project_id: str
    chapter_id: str | None = None
    type: CreativeReminderType
    severity: CreativeReminderSeverity
    title: str
    message: str
    target_type: CreativeReminderTargetType
    target_id: str
    action_label: str
    created_from: Literal["rule"] = "rule"


class CreativeReminderList(BaseModel):
    total: int
    items: list[CreativeReminderRead]
