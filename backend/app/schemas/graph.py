from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


GraphNodeType = Literal["character", "setting", "clue", "timeline_event", "organization", "location", "custom"]
GraphNodeBoundType = Literal["character", "setting", "clue", "timeline_event", "custom"]
GraphVisibility = Literal["normal", "subtle", "hidden"]
GraphEdgeRelationType = Literal[
    "relationship",
    "conflict",
    "ally",
    "family",
    "belongs_to",
    "controls",
    "clue_related",
    "timeline_related",
    "setting_related",
    "cause",
    "custom",
]
GraphEdgeDirection = Literal["directed", "undirected"]
GraphEdgeLineStyle = Literal["solid", "dashed", "dotted", "arc"]


class GraphNodeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    node_type: GraphNodeType
    bound_type: GraphNodeBoundType | None = None
    bound_id: str | None = None
    summary: str = ""
    x: float = 0
    y: float = 0
    color: str | None = None
    size: int = Field(default=1, ge=1)
    visibility: GraphVisibility = "normal"

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class GraphNodeCreate(GraphNodeBase):
    pass


class GraphNodeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    node_type: GraphNodeType | None = None
    bound_type: GraphNodeBoundType | None = None
    bound_id: str | None = None
    summary: str | None = None
    x: float | None = None
    y: float | None = None
    color: str | None = None
    size: int | None = Field(default=None, ge=1)
    visibility: GraphVisibility | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title


class GraphNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    node_type: str
    bound_type: str | None
    bound_id: str | None
    summary: str
    x: float
    y: float
    color: str | None
    size: int
    visibility: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class GraphEdgeBase(BaseModel):
    from_node_id: str
    to_node_id: str
    relation_type: GraphEdgeRelationType
    direction: GraphEdgeDirection = "undirected"
    strength: int = Field(default=1, ge=1, le=5)
    label: str = ""
    note: str = ""
    line_style: GraphEdgeLineStyle = "solid"
    visibility: GraphVisibility = "normal"

    @model_validator(mode="after")
    def validate_distinct_nodes(self):
        if self.from_node_id == self.to_node_id:
            raise ValueError("from_node_id and to_node_id must not be the same")
        return self


class GraphEdgeCreate(GraphEdgeBase):
    pass


class GraphEdgeUpdate(BaseModel):
    from_node_id: str | None = None
    to_node_id: str | None = None
    relation_type: GraphEdgeRelationType | None = None
    direction: GraphEdgeDirection | None = None
    strength: int | None = Field(default=None, ge=1, le=5)
    label: str | None = None
    note: str | None = None
    line_style: GraphEdgeLineStyle | None = None
    visibility: GraphVisibility | None = None

    @model_validator(mode="after")
    def validate_distinct_nodes(self):
        if self.from_node_id is not None and self.to_node_id is not None and self.from_node_id == self.to_node_id:
            raise ValueError("from_node_id and to_node_id must not be the same")
        return self


class GraphEdgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    from_node_id: str
    to_node_id: str
    relation_type: str
    direction: str
    strength: int
    label: str
    note: str
    line_style: str
    visibility: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
