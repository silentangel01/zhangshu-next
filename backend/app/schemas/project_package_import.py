from pydantic import BaseModel


class ProjectPackageEntityCounts(BaseModel):
    volumes: int = 0
    chapters: int = 0
    chapter_versions: int = 0
    characters: int = 0
    settings: int = 0
    clues: int = 0
    outlines: int = 0
    timeline_tracks: int = 0
    timeline_events: int = 0
    timeline_edges: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    chapter_characters: int = 0
    chapter_clues: int = 0
    chapter_settings: int = 0
    clue_characters: int = 0
    clue_settings: int = 0


class ProjectPackageImportPreviewResponse(BaseModel):
    preview_id: str
    project_title: str
    source_version: int
    entity_counts: ProjectPackageEntityCounts
    has_cover: bool
    warnings: list[str]


class ProjectPackageImportConfirmRequest(BaseModel):
    preview_id: str


class ProjectPackageImportConfirmResponse(BaseModel):
    project_id: str
    project_title: str
    entity_counts: ProjectPackageEntityCounts
    warnings: list[str]
