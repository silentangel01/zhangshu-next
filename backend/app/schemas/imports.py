from typing import Literal

from pydantic import BaseModel


ImportType = Literal["legacy_json", "folder_zip", "external_files"]
ImportMode = Literal["create_project", "append_project"]


class ImportPreviewVolume(BaseModel):
    temp_id: str
    title: str
    order_index: int
    chapter_count: int
    chapters: list[str] = []


class ImportPreviewReport(BaseModel):
    files_detected: list[str]
    files_skipped: list[str]
    encoding_issues: list[str]
    empty_files: list[str]
    duplicate_titles: list[str]
    unsupported_files: list[str]


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
    unassigned_chapters: list[str] = []
    warnings: list[str]
    unsupported_items: list[str]
    failed_files: list[str]
    report: ImportPreviewReport
    can_import: bool


class ConfirmImportRequest(BaseModel):
    import_id: str | None = None
    mode: ImportMode = "create_project"
    project_id: str | None = None
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
