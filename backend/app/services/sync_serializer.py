"""Sync serializer — serialize/deserialize entities for cloud sync.

Supports 24 P0/P1 entity types (L1 + L2 + L3):
P0: projects, volumes, chapters, characters, setting_items, clues,
    outline_items, timeline_tracks, timeline_events, timeline_edges,
    graph_nodes, graph_edges.
P1: chapter_characters, chapter_settings, chapter_clues,
    clue_characters, clue_settings,
    timeline_event_characters, timeline_event_settings, timeline_event_clues,
    outline_item_characters, outline_item_settings, outline_item_clues,
    outline_item_timeline_events.

All timestamps are output as ISO 8601 UTC strings.
``projects.cover_image_path`` is treated as local-only and cleared on export.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect as sqla_inspect
from sqlalchemy.orm import Session

from app.models.character import Character
from app.models.chapter import Chapter
from app.models.chapter_character import ChapterCharacter
from app.models.chapter_clue import ChapterClue
from app.models.chapter_setting import ChapterSetting
from app.models.clue import Clue
from app.models.clue_character import ClueCharacter
from app.models.clue_setting import ClueSetting
from app.models.graph_edge import GraphEdge
from app.models.graph_node import GraphNode
from app.models.outline_item import OutlineItem
from app.models.outline_item_character import OutlineItemCharacter
from app.models.outline_item_clue import OutlineItemClue
from app.models.outline_item_setting import OutlineItemSetting
from app.models.outline_item_timeline_event import OutlineItemTimelineEvent
from app.models.project import Project
from app.models.setting_item import SettingItem
from app.models.timeline_edge import TimelineEdge
from app.models.timeline_event import TimelineEvent
from app.models.timeline_event_character import TimelineEventCharacter
from app.models.timeline_event_clue import TimelineEventClue
from app.models.timeline_event_setting import TimelineEventSetting
from app.models.timeline_track import TimelineTrack
from app.models.volume import Volume

logger = logging.getLogger(__name__)

# P0/P1 entity model registry (L1 + L2 + L3)
SYNC_ENTITY_MODELS: dict[str, type] = {
    # P0 entities
    "projects": Project,
    "volumes": Volume,
    "chapters": Chapter,
    "characters": Character,
    "setting_items": SettingItem,
    "clues": Clue,
    "outline_items": OutlineItem,
    "timeline_tracks": TimelineTrack,
    "timeline_events": TimelineEvent,
    "timeline_edges": TimelineEdge,
    "graph_nodes": GraphNode,
    "graph_edges": GraphEdge,
    # P1 join entities
    "chapter_characters": ChapterCharacter,
    "chapter_settings": ChapterSetting,
    "chapter_clues": ChapterClue,
    "clue_characters": ClueCharacter,
    "clue_settings": ClueSetting,
    "timeline_event_characters": TimelineEventCharacter,
    "timeline_event_settings": TimelineEventSetting,
    "timeline_event_clues": TimelineEventClue,
    "outline_item_characters": OutlineItemCharacter,
    "outline_item_settings": OutlineItemSetting,
    "outline_item_clues": OutlineItemClue,
    "outline_item_timeline_events": OutlineItemTimelineEvent,
}

# Apply order: respects FK dependencies (parents before children, P0 before P1)
SYNC_APPLY_ORDER = [
    # P0 entities
    "projects",
    "volumes",
    "chapters",
    "characters",
    "setting_items",
    "clues",
    "outline_items",
    "timeline_tracks",
    "timeline_events",
    "timeline_edges",
    "graph_nodes",
    "graph_edges",
    # P1 join entities
    "chapter_characters",
    "chapter_settings",
    "chapter_clues",
    "clue_characters",
    "clue_settings",
    "timeline_event_characters",
    "timeline_event_settings",
    "timeline_event_clues",
    "outline_item_characters",
    "outline_item_settings",
    "outline_item_clues",
    "outline_item_timeline_events",
]

# Delete order: reverse of apply (P1 before P0, children before parents)
SYNC_DELETE_ORDER = [
    # P1 join entities (deleted first)
    "outline_item_timeline_events",
    "outline_item_clues",
    "outline_item_settings",
    "outline_item_characters",
    "timeline_event_clues",
    "timeline_event_settings",
    "timeline_event_characters",
    "clue_settings",
    "clue_characters",
    "chapter_clues",
    "chapter_settings",
    "chapter_characters",
    # P0 entities
    "graph_edges",
    "graph_nodes",
    "timeline_edges",
    "timeline_events",
    "timeline_tracks",
    "outline_items",
    "clues",
    "setting_items",
    "characters",
    "chapters",
    "volumes",
    "projects",
]

# Fields to exclude from serialization (local-only or auto-managed)
_EXCLUDE_FIELDS: dict[str, set[str]] = {
    # P0
    "projects": {"cover_image_path"},
    "volumes": set(),
    "chapters": set(),
    "characters": set(),
    "setting_items": set(),
    "clues": set(),
    "outline_items": set(),
    "timeline_tracks": set(),
    "timeline_events": set(),
    "timeline_edges": set(),
    "graph_nodes": set(),
    "graph_edges": set(),
    # P1
    "chapter_characters": set(),
    "chapter_settings": set(),
    "chapter_clues": set(),
    "clue_characters": set(),
    "clue_settings": set(),
    "timeline_event_characters": set(),
    "timeline_event_settings": set(),
    "timeline_event_clues": set(),
    "outline_item_characters": set(),
    "outline_item_settings": set(),
    "outline_item_clues": set(),
    "outline_item_timeline_events": set(),
}


def _to_utc_iso(value: Any) -> str | None:
    """Convert a datetime to ISO 8601 UTC string, or None if not a datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def serialize_entity(entity: Any, entity_type: str) -> dict[str, Any]:
    """Serialize a SQLAlchemy model instance to a JSON-safe dict.

    - All datetime fields are converted to ISO 8601 UTC strings.
    - Fields in ``_EXCLUDE_FIELDS[entity_type]`` are cleared/omitted.
    """
    mapper = sqla_inspect(entity)
    columns = mapper.mapper.column_attrs
    excludes = _EXCLUDE_FIELDS.get(entity_type, set())

    payload: dict[str, Any] = {}
    for attr in columns:
        col_name = attr.key
        if col_name in excludes:
            # For cover_image_path, output empty string instead of local path
            payload[col_name] = None
            continue
        value = getattr(entity, col_name)
        if isinstance(value, datetime):
            payload[col_name] = _to_utc_iso(value)
        else:
            payload[col_name] = value

    return payload


def deserialize_entity(payload: dict[str, Any], entity_type: str) -> dict[str, Any]:
    """Convert a sync payload dict back to kwargs suitable for model construction.

    - ISO 8601 strings are parsed back to datetime objects.
    - Fields not in the model are silently dropped.
    """
    model_cls = SYNC_ENTITY_MODELS.get(entity_type)
    if model_cls is None:
        logger.warning("Unknown entity type for deserialization: %s", entity_type)
        return payload

    mapper = sqla_inspect(model_cls)
    column_names = {attr.key for attr in mapper.mapper.column_attrs}

    result: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in column_names:
            continue
        # Parse ISO datetime strings back to datetime objects
        col = mapper.mapper.column_attrs[key].columns[0]
        col_type_name = type(col.type).__name__
        if col_type_name == "DateTime" and isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                result[key] = parsed
            except (ValueError, TypeError):
                result[key] = value
        else:
            result[key] = value

    return result


def get_entity_by_id(db: Session, entity_type: str, entity_id: str) -> Any | None:
    """Fetch a single entity by type and ID, including soft-deleted ones."""
    model_cls = SYNC_ENTITY_MODELS.get(entity_type)
    if model_cls is None:
        return None
    return db.get(model_cls, entity_id)


def get_active_entity(db: Session, entity_type: str, entity_id: str) -> Any | None:
    """Fetch a single active (non-deleted) entity by type and ID."""
    entity = get_entity_by_id(db, entity_type, entity_id)
    if entity is None:
        return None
    if hasattr(entity, "deleted_at") and entity.deleted_at is not None:
        return None
    return entity


def payload_to_json(payload: dict[str, Any]) -> str:
    """Serialize a payload dict to canonical JSON for hashing/storage."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
