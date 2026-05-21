from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
import json
from typing import Any
from uuid import uuid4
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from sqlalchemy import DateTime, select
from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.chapter_character import ChapterCharacter
from app.models.chapter_clue import ChapterClue
from app.models.chapter_setting import ChapterSetting
from app.models.chapter_version import ChapterVersion
from app.models.character import Character
from app.models.clue import Clue
from app.models.clue_character import ClueCharacter
from app.models.clue_setting import ClueSetting
from app.models.graph_edge import GraphEdge
from app.models.graph_node import GraphNode
from app.models.outline_item import OutlineItem
from app.models.project import Project
from app.models.setting_item import SettingItem
from app.models.timeline_edge import TimelineEdge
from app.models.timeline_event import TimelineEvent
from app.models.timeline_track import TimelineTrack
from app.models.volume import Volume
from app.schemas.backup import RestoreCounts, RestoreReport


BACKUP_FORMAT = "zhangshu.project_backup"
BACKUP_VERSION = 1


class BackupProjectNotFoundError(Exception):
    pass


class BackupInvalidError(Exception):
    pass


@dataclass
class BackupFile:
    filename: str
    content: BytesIO


ENTITY_MODELS = {
    "project": Project,
    "volumes": Volume,
    "chapters": Chapter,
    "chapter_versions": ChapterVersion,
    "characters": Character,
    "settings": SettingItem,
    "clues": Clue,
    "timeline_tracks": TimelineTrack,
    "timeline_events": TimelineEvent,
    "timeline_edges": TimelineEdge,
    "graph_nodes": GraphNode,
    "graph_edges": GraphEdge,
    "outlines": OutlineItem,
    "chapter_characters": ChapterCharacter,
    "chapter_clues": ChapterClue,
    "chapter_settings": ChapterSetting,
    "clue_characters": ClueCharacter,
    "clue_settings": ClueSetting,
}


PROJECT_CHILDREN = [
    "volumes",
    "chapters",
    "chapter_versions",
    "characters",
    "settings",
    "clues",
    "timeline_tracks",
    "timeline_events",
    "timeline_edges",
    "graph_nodes",
    "graph_edges",
    "outlines",
    "chapter_characters",
    "chapter_clues",
    "chapter_settings",
    "clue_characters",
    "clue_settings",
]


RESTORE_ORDER = [
    "volumes",
    "chapters",
    "chapter_versions",
    "characters",
    "settings",
    "clues",
    "outlines",
    "timeline_tracks",
    "timeline_events",
    "timeline_edges",
    "graph_nodes",
    "graph_edges",
    "chapter_characters",
    "chapter_clues",
    "chapter_settings",
    "clue_characters",
    "clue_settings",
]


REFERENCE_FIELDS = {
    "volumes": {"project_id": "project"},
    "chapters": {"project_id": "project", "volume_id": "volumes"},
    "chapter_versions": {"project_id": "project", "chapter_id": "chapters"},
    "characters": {"project_id": "project"},
    "settings": {"project_id": "project", "parent_id": "settings"},
    "clues": {
        "project_id": "project",
        "setup_chapter_id": "chapters",
        "payoff_chapter_id": "chapters",
    },
    "timeline_tracks": {"project_id": "project", "bound_id": "__bound__"},
    "timeline_events": {
        "project_id": "project",
        "track_id": "timeline_tracks",
        "chapter_id": "chapters",
        "location_setting_id": "settings",
    },
    "timeline_edges": {
        "project_id": "project",
        "from_event_id": "timeline_events",
        "to_event_id": "timeline_events",
    },
    "graph_nodes": {"project_id": "project", "bound_id": "__bound__"},
    "graph_edges": {
        "project_id": "project",
        "from_node_id": "graph_nodes",
        "to_node_id": "graph_nodes",
    },
    "outlines": {
        "project_id": "project",
        "parent_id": "outlines",
        "volume_id": "volumes",
        "chapter_id": "chapters",
    },
    "chapter_characters": {
        "project_id": "project",
        "chapter_id": "chapters",
        "character_id": "characters",
    },
    "chapter_clues": {
        "project_id": "project",
        "chapter_id": "chapters",
        "clue_id": "clues",
    },
    "chapter_settings": {
        "project_id": "project",
        "chapter_id": "chapters",
        "setting_item_id": "settings",
    },
    "clue_characters": {
        "project_id": "project",
        "clue_id": "clues",
        "character_id": "characters",
    },
    "clue_settings": {
        "project_id": "project",
        "clue_id": "clues",
        "setting_item_id": "settings",
    },
}


BOUND_TYPE_TO_ENTITY = {
    "chapter": "chapters",
    "character": "characters",
    "setting": "settings",
    "setting_item": "settings",
    "clue": "clues",
    "timeline_event": "timeline_events",
    "timeline_track": "timeline_tracks",
    "graph_node": "graph_nodes",
    "outline": "outlines",
}


class BackupService:
    def __init__(self, db: Session):
        self.db = db

    def export_project_backup(self, project_id: str) -> BackupFile:
        project = self.db.get(Project, project_id)
        if project is None or project.deleted_at is not None:
            raise BackupProjectNotFoundError()

        payload = self._build_payload(project)
        manifest = payload["manifest"]

        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as backup_zip:
            backup_zip.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            backup_zip.writestr(
                "project.json",
                json.dumps(payload["project"], ensure_ascii=False, indent=2),
            )
            for entity_name in PROJECT_CHILDREN:
                backup_zip.writestr(
                    f"data/{entity_name}.json",
                    json.dumps(payload[entity_name], ensure_ascii=False, indent=2),
                )

        buffer.seek(0)
        safe_title = "".join(
            char if char.isascii() and (char.isalnum() or char in ("-", "_")) else "_"
            for char in project.title.strip()
        ).strip("_") or "project"
        return BackupFile(
            filename=f"{safe_title}_backup_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.zip",
            content=buffer,
        )

    def restore_project_backup(self, content: bytes) -> RestoreReport:
        payload = self._read_payload(content)
        warnings: list[str] = []
        errors: list[str] = []
        id_maps: dict[str, dict[str, str]] = {"project": {}}

        try:
            project_data = dict(payload["project"])
            old_project_id = project_data["id"]
            new_project_id = str(uuid4())
            id_maps["project"][old_project_id] = new_project_id

            project_data["id"] = new_project_id
            project_data["title"] = self._copy_title(str(project_data.get("title") or "未命名项目"))
            project_data["created_at"] = datetime.now(timezone.utc)
            project_data["updated_at"] = datetime.now(timezone.utc)
            project_data["deleted_at"] = None

            self.db.add(Project(**self._deserialize_row("project", project_data)))
            self.db.flush()

            for entity_name in RESTORE_ORDER:
                id_maps[entity_name] = {}
                for row in payload.get(entity_name, []):
                    id_maps[entity_name][str(row["id"])] = str(uuid4())

            for entity_name in RESTORE_ORDER:
                for row in payload.get(entity_name, []):
                    restored_row = self._restore_row(entity_name, row, id_maps, warnings)
                    if restored_row is None:
                        continue
                    self.db.add(ENTITY_MODELS[entity_name](**restored_row))
                self.db.flush()

            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise BackupInvalidError() from exc

        return RestoreReport(
            project_id=new_project_id,
            project_title=project_data["title"],
            counts=RestoreCounts(
                volumes=len(id_maps.get("volumes", {})),
                chapters=len(id_maps.get("chapters", {})),
                materials=self._material_count(id_maps),
            ),
            warnings=warnings,
            errors=errors,
        )

    def _build_payload(self, project: Project) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "project": self._serialize_model(project),
        }

        for entity_name in PROJECT_CHILDREN:
            model = ENTITY_MODELS[entity_name]
            records = self.db.scalars(
                select(model)
                .where(model.project_id == project.id)
                .order_by(model.created_at.asc() if hasattr(model, "created_at") else model.id.asc())
            ).all()
            payload[entity_name] = [self._serialize_model(record) for record in records]

        payload["manifest"] = {
            "format": BACKUP_FORMAT,
            "version": BACKUP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "project": {
                "id": project.id,
                "title": project.title,
                "version": project.version,
            },
            "tables": {
                "project": 1,
                **{entity_name: len(payload[entity_name]) for entity_name in PROJECT_CHILDREN},
            },
            "notes": [
                "This backup is intended for restoring a Zhangshu project, not for manuscript export.",
                "Browser-local recovery drafts are not included because they are stored outside the backend database.",
            ],
        }
        return payload

    def _read_payload(self, content: bytes) -> dict[str, Any]:
        try:
            with ZipFile(BytesIO(content), "r") as backup_zip:
                manifest = json.loads(backup_zip.read("manifest.json").decode("utf-8"))
                if (
                    manifest.get("format") != BACKUP_FORMAT
                    or manifest.get("version") != BACKUP_VERSION
                ):
                    raise BackupInvalidError()

                payload: dict[str, Any] = {
                    "manifest": manifest,
                    "project": json.loads(backup_zip.read("project.json").decode("utf-8")),
                }
                for entity_name in PROJECT_CHILDREN:
                    path = f"data/{entity_name}.json"
                    payload[entity_name] = (
                        json.loads(backup_zip.read(path).decode("utf-8"))
                        if path in backup_zip.namelist()
                        else []
                    )
                return payload
        except (BadZipFile, KeyError, json.JSONDecodeError) as exc:
            raise BackupInvalidError() from exc

    def _restore_row(
        self,
        entity_name: str,
        source_row: dict[str, Any],
        id_maps: dict[str, dict[str, str]],
        warnings: list[str],
    ) -> dict[str, Any] | None:
        row = dict(source_row)
        old_id = str(row["id"])
        new_id = id_maps[entity_name][old_id]

        for field_name, target_entity in REFERENCE_FIELDS[entity_name].items():
            if row.get(field_name) is None:
                continue
            if target_entity == "__bound__":
                row[field_name] = self._map_bound_id(entity_name, row, id_maps, warnings)
                continue
            mapped_id = id_maps.get(target_entity, {}).get(str(row[field_name]))
            if mapped_id is None:
                warnings.append(f"{entity_name}.{field_name} 引用缺失，已跳过一条记录")
                return None
            row[field_name] = mapped_id

        row["id"] = new_id
        return self._deserialize_row(entity_name, row)

    def _map_bound_id(
        self,
        entity_name: str,
        row: dict[str, Any],
        id_maps: dict[str, dict[str, str]],
        warnings: list[str],
    ) -> str | None:
        bound_id = row.get("bound_id")
        bound_type = row.get("bound_type")
        if bound_id is None or bound_type is None:
            return bound_id

        target_entity = BOUND_TYPE_TO_ENTITY.get(str(bound_type))
        if target_entity is None:
            return bound_id

        mapped_id = id_maps.get(target_entity, {}).get(str(bound_id))
        if mapped_id is None:
            warnings.append(f"{entity_name}.bound_id 引用缺失，已清空绑定")
            return None
        return mapped_id

    def _serialize_model(self, model: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

    def _deserialize_row(self, entity_name: str, row: dict[str, Any]) -> dict[str, Any]:
        model = ENTITY_MODELS[entity_name]
        result = dict(row)
        for column in model.__table__.columns:
            value = result.get(column.name)
            if value is not None and isinstance(column.type, DateTime) and isinstance(value, str):
                result[column.name] = datetime.fromisoformat(value)
        return result

    def _copy_title(self, title: str) -> str:
        base_title = f"{title}（备份恢复）"
        existing_titles = set(
            self.db.scalars(
                select(Project.title).where(Project.title.like(f"{base_title}%"))
            ).all()
        )
        if base_title not in existing_titles:
            return base_title

        index = 2
        while f"{base_title} {index}" in existing_titles:
            index += 1
        return f"{base_title} {index}"

    def _material_count(self, id_maps: dict[str, dict[str, str]]) -> int:
        return sum(
            len(id_maps.get(entity_name, {}))
            for entity_name in ("characters", "settings", "clues", "outlines")
        )
