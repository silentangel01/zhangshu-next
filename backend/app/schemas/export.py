from enum import Enum

from pydantic import BaseModel, model_validator


class ExportScope(str, Enum):
    project = "project"
    volume = "volume"
    chapter = "chapter"


class ExportFormat(str, Enum):
    txt = "txt"
    md = "md"
    docx = "docx"


class ManuscriptExportRequest(BaseModel):
    scope: ExportScope
    volume_id: str | None = None
    chapter_id: str | None = None
    format: ExportFormat

    @model_validator(mode="after")
    def validate_scope_target(self):
        if self.scope == ExportScope.volume and not self.volume_id:
            raise ValueError("volume_id is required for volume export")
        if self.scope == ExportScope.chapter and not self.chapter_id:
            raise ValueError("chapter_id is required for chapter export")
        return self
