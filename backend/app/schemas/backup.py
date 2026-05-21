from pydantic import BaseModel


class RestoreCounts(BaseModel):
    volumes: int
    chapters: int
    materials: int


class RestoreReport(BaseModel):
    project_id: str
    project_title: str
    counts: RestoreCounts
    warnings: list[str]
    errors: list[str]
