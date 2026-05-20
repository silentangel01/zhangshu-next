from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy.orm import Session

from app.infrastructure.database import DATABASE_DIR
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.volume import Volume
from app.schemas.imports import ConfirmImportRequest
from app.utils.import_parsers import (
    calculate_word_count,
    parse_folder_zip_bytes,
    parse_legacy_json_bytes,
)


IMPORTS_DIR = DATABASE_DIR / "imports"
IMPORTS_TMP_DIR = IMPORTS_DIR / "tmp"
IMPORTS_REPORTS_DIR = IMPORTS_DIR / "reports"


class ImportPreviewNotFoundError(Exception):
    pass


class ImportPreviewInvalidError(Exception):
    pass


class ImportService:
    def __init__(self, db: Session):
        self.db = db
        ensure_import_directories()

    def preview_import(
        self,
        *,
        import_type: str,
        source_filename: str,
        content: bytes,
    ) -> dict[str, Any]:
        import_id = str(uuid.uuid4())
        safe_source_filename = Path(source_filename).name or f"{import_id}.upload"
        temp_dir = IMPORTS_TMP_DIR / import_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        (temp_dir / safe_source_filename).write_bytes(content)

        if import_type == "legacy_json":
            preview = parse_legacy_json_bytes(content, safe_source_filename)
        elif import_type == "folder_zip":
            preview = parse_folder_zip_bytes(content, safe_source_filename)
            self._safe_extract_zip(content, temp_dir / "extracted")
        else:
            raise ImportPreviewInvalidError

        preview["import_id"] = import_id
        self._write_preview(import_id, preview)
        return self._to_preview_response(preview)

    def confirm_import(self, import_id: str, data: ConfirmImportRequest) -> dict[str, Any]:
        preview = self._load_preview(import_id)
        if not preview.get("can_import"):
            raise ImportPreviewInvalidError

        project_title = (data.project_title or preview["detected_project_title"]).strip()
        if not project_title:
            project_title = "未命名导入项目"

        try:
            project = Project(
                id=str(uuid.uuid4()),
                title=project_title,
                summary=preview.get("summary"),
            )
            self.db.add(project)

            created_volume_count = 0
            created_chapter_count = 0

            for volume_data in preview.get("volumes", []):
                volume = Volume(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    title=volume_data["title"],
                    order_index=volume_data["order_index"],
                )
                self.db.add(volume)
                created_volume_count += 1

                for chapter_data in volume_data.get("chapters", []):
                    self._add_chapter(project.id, volume.id, chapter_data)
                    created_chapter_count += 1

            for chapter_data in preview.get("unassigned_chapters", []):
                self._add_chapter(project.id, None, chapter_data)
                created_chapter_count += 1

            report = self._write_report(
                import_id=import_id,
                preview=preview,
                created_project_id=project.id,
                created_volume_count=created_volume_count,
                created_chapter_count=created_chapter_count,
            )
            self.db.commit()
            return report
        except Exception:
            self.db.rollback()
            raise

    def _add_chapter(
        self,
        project_id: str,
        volume_id: str | None,
        chapter_data: dict[str, Any],
    ) -> None:
        content = chapter_data.get("content") or ""
        self.db.add(
            Chapter(
                id=str(uuid.uuid4()),
                project_id=project_id,
                volume_id=volume_id,
                title=chapter_data["title"],
                content=content,
                order_index=chapter_data["order_index"],
                status="draft",
                word_count=calculate_word_count(content),
            )
        )

    def _write_preview(self, import_id: str, preview: dict[str, Any]) -> None:
        preview_path = IMPORTS_DIR / f"{import_id}.json"
        preview_path.write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_preview(self, import_id: str) -> dict[str, Any]:
        preview_path = IMPORTS_DIR / f"{import_id}.json"
        if not preview_path.exists():
            raise ImportPreviewNotFoundError
        return json.loads(preview_path.read_text(encoding="utf-8"))

    def _write_report(
        self,
        *,
        import_id: str,
        preview: dict[str, Any],
        created_project_id: str,
        created_volume_count: int,
        created_chapter_count: int,
    ) -> dict[str, Any]:
        report_id = str(uuid.uuid4())
        report_path = IMPORTS_REPORTS_DIR / f"{report_id}.json"
        report = {
            "import_id": import_id,
            "import_type": preview["import_type"],
            "source_filename": preview["source_filename"],
            "created_project_id": created_project_id,
            "created_volume_count": created_volume_count,
            "created_chapter_count": created_chapter_count,
            "total_word_count": preview["total_word_count"],
            "warnings": preview["warnings"],
            "unsupported_items": preview["unsupported_items"],
            "failed_files": preview["failed_files"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_id": report_id,
            "report_path": str(report_path),
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    def _to_preview_response(self, preview: dict[str, Any]) -> dict[str, Any]:
        return {
            "import_id": preview["import_id"],
            "import_type": preview["import_type"],
            "detected_project_title": preview["detected_project_title"],
            "summary": preview.get("summary"),
            "volume_count": preview["volume_count"],
            "chapter_count": preview["chapter_count"],
            "total_word_count": preview["total_word_count"],
            "volumes": [
                {
                    "temp_id": volume["temp_id"],
                    "title": volume["title"],
                    "order_index": volume["order_index"],
                    "chapter_count": len(volume.get("chapters", [])),
                }
                for volume in preview.get("volumes", [])
            ],
            "unassigned_chapter_count": preview["unassigned_chapter_count"],
            "warnings": preview["warnings"],
            "unsupported_items": preview["unsupported_items"],
            "failed_files": preview["failed_files"],
            "can_import": preview["can_import"],
        }

    def _safe_extract_zip(self, content: bytes, target_dir: Path) -> None:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(io_bytes(content)) as archive:
            for info in archive.infolist():
                path = PurePosixPath(info.filename)
                if any(part == ".." for part in path.parts) or path.is_absolute():
                    continue

                destination = target_dir.joinpath(*path.parts)
                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue

                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(info))


def ensure_import_directories() -> None:
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    IMPORTS_TMP_DIR.mkdir(parents=True, exist_ok=True)
    IMPORTS_REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def io_bytes(content: bytes):
    import io

    return io.BytesIO(content)
