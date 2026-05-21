from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecoveryDraftCreate(BaseModel):
    content: str
    saved_content_snapshot: str = ""


class RecoveryDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    chapter_id: str
    content: str
    saved_content_snapshot: str
    word_count: int
    created_at: datetime
    updated_at: datetime
