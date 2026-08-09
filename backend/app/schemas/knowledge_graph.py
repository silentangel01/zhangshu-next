from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


KnowledgeGraphStatus = Literal["candidate", "accepted", "rejected"]
KnowledgeGraphExtractionStatus = Literal["pending", "running", "completed", "failed"]
KnowledgeGraphExtractionScope = Literal["project", "source"]
KnowledgeGraphEntityType = Literal[
    "character",
    "setting",
    "location",
    "organization",
    "item",
    "event",
    "clue",
    "concept",
    "custom",
]
KnowledgeGraphRelationType = Literal[
    "relationship",
    "conflict",
    "ally",
    "family",
    "belongs_to",
    "located_in",
    "controls",
    "causes",
    "reveals",
    "foreshadows",
    "setting_related",
    "timeline_related",
    "custom",
]
KnowledgeGraphFactStatus = Literal[
    "confirmed",
    "claimed",
    "rumor",
    "hypothesis",
    "dream",
    "plan",
    "deprecated",
]


class KnowledgeGraphExtractionRunCreate(BaseModel):
    scope: KnowledgeGraphExtractionScope = "source"
    source_id: str | None = None
    max_chunks: int = Field(default=40, ge=1, le=80)
    privacy_confirmed: bool = False

    @field_validator("source_id")
    @classmethod
    def source_id_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class KnowledgeGraphExtractionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    scope: str
    source_id: str | None
    status: str
    model_name: str
    total_chunks: int
    processed_chunks: int
    candidate_entity_count: int
    candidate_relation_count: int
    error_message: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    deleted_at: datetime | None


class KnowledgeGraphRunList(BaseModel):
    total: int
    items: list[KnowledgeGraphExtractionRunRead]


class KnowledgeGraphEntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    canonical_name: str
    entity_type: str
    aliases_json: str
    description: str
    bound_type: str | None
    bound_id: str | None
    status: str
    confidence: float
    source_count: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class KnowledgeGraphEntityList(BaseModel):
    total: int
    items: list[KnowledgeGraphEntityRead]


class KnowledgeGraphEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    entity_id: str | None
    relation_id: str | None
    source_id: str
    source_title: str
    chunk_id: str | None
    chunk_heading: str
    evidence_text: str
    char_start: int | None
    char_end: int | None
    extraction_run_id: str | None
    created_at: datetime
    deleted_at: datetime | None


class KnowledgeGraphRelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    subject_entity_id: str
    object_entity_id: str
    relation_type: str
    predicate_text: str
    direction: str
    fact_status: str
    status: str
    confidence: float
    note: str
    source_count: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int
    subject: KnowledgeGraphEntityRead
    object: KnowledgeGraphEntityRead
    evidence: list[KnowledgeGraphEvidenceRead] = Field(default_factory=list)


class KnowledgeGraphRelationList(BaseModel):
    total: int
    items: list[KnowledgeGraphRelationRead]


class KnowledgeGraphSubgraphNode(BaseModel):
    id: str
    label: str
    entity_type: str
    status: str
    confidence: float


class KnowledgeGraphSubgraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    relation_type: str
    fact_status: str
    confidence: float


class KnowledgeGraphSubgraph(BaseModel):
    nodes: list[KnowledgeGraphSubgraphNode]
    edges: list[KnowledgeGraphSubgraphEdge]
