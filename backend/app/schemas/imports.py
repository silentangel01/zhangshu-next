from typing import Literal

from pydantic import BaseModel


ImportType = Literal["legacy_json", "folder_zip"]
ImportMode = Literal["create_project"]


class ImportPreviewVolume(BaseModel):
    temp_id: str
    title: str
    order_index: int
    chapter_count: int


class ImportPreviewResponse(BaseModel):
    import_id: str
    import_type: str
    detected_project_title: str
    summary: str | None
    volume_count: int
    chapter_count: int
    total_word_count: int
    volumes: list[ImportPreviewVolume]
    unassigned_chapter_count: int
    warnings: list[str]
    unsupported_items: list[str]
    failed_files: list[str]
    can_import: bool


class ConfirmImportRequest(BaseModel):
    mode: ImportMode = "create_project"
    project_title: str | None = None


class ImportConfirmResponse(BaseModel):
    created_project_id: str
    created_volume_count: int
    created_chapter_count: int
    total_word_count: int
    warnings: list[str]
    unsupported_items: list[str]
    failed_files: list[str]
    report_id: str
    report_path: str
