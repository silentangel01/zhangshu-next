from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.schemas.backup import RestoreReport
from app.schemas.project_package_import import (
    ProjectPackageEntityCounts,
    ProjectPackageImportConfirmResponse,
    ProjectPackageImportPreviewResponse,
)
from app.services.backup_service import BackupInvalidError, BackupService


class ProjectPackagePreviewNotFoundError(Exception):
    pass


_PREVIEW_DIR = Path(tempfile.gettempdir()) / "zhangshu_package_previews"
_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


class ProjectPackageImportService:
    def __init__(self, db: Session):
        self.db = db
        self._backup_service = BackupService(db)

    def preview_package(self, content: bytes) -> ProjectPackageImportPreviewResponse:
        try:
            inspection = self._backup_service.inspect_project_backup(content)
        except BackupInvalidError:
            raise

        preview_id = str(uuid4())
        preview_file = _PREVIEW_DIR / f"{preview_id}.zip"
        preview_file.write_bytes(content)

        counts = ProjectPackageEntityCounts(**inspection["entity_counts"])
        return ProjectPackageImportPreviewResponse(
            preview_id=preview_id,
            project_title=inspection["project_title"],
            source_version=inspection["source_version"],
            entity_counts=counts,
            has_cover=inspection["has_cover"],
            warnings=inspection["warnings"],
        )

    def confirm_package(
        self, preview_id: str
    ) -> ProjectPackageImportConfirmResponse:
        preview_file = _PREVIEW_DIR / f"{preview_id}.zip"
        if not preview_file.exists():
            raise ProjectPackagePreviewNotFoundError()

        content = preview_file.read_bytes()
        preview_file.unlink(missing_ok=True)

        inspection = self._backup_service.inspect_project_backup(content)
        payload: dict[str, Any] = inspection["_payload"]

        report: RestoreReport = self._backup_service.restore_from_payload(payload)

        counts = ProjectPackageEntityCounts(**inspection["entity_counts"])
        return ProjectPackageImportConfirmResponse(
            project_id=report.project_id,
            project_title=report.project_title,
            entity_counts=counts,
            warnings=report.warnings,
        )
