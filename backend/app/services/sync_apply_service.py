"""Sync apply service — apply remote cloud changes to local SQLite.

When applying remote changes, we do NOT call the normal business services
(e.g. ChapterService) to avoid side effects like creating chapter_versions
or writing_stats entries.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.sync_serializer import (
    SYNC_APPLY_ORDER,
    SYNC_DELETE_ORDER,
    SYNC_ENTITY_MODELS,
    deserialize_entity,
    get_active_entity,
    get_entity_by_id,
)

logger = logging.getLogger(__name__)

# P1 join tables and their parent entity dependencies.
# Each entry maps: field_name -> parent_entity_type
_P1_DEPENDENCY_MAP: dict[str, dict[str, str]] = {
    "chapter_characters": {"chapter_id": "chapters", "character_id": "characters"},
    "chapter_settings": {"chapter_id": "chapters", "setting_item_id": "setting_items"},
    "chapter_clues": {"chapter_id": "chapters", "clue_id": "clues"},
    "clue_characters": {"clue_id": "clues", "character_id": "characters"},
    "clue_settings": {"clue_id": "clues", "setting_item_id": "setting_items"},
    "timeline_event_characters": {
        "timeline_event_id": "timeline_events",
        "character_id": "characters",
    },
    "timeline_event_settings": {
        "timeline_event_id": "timeline_events",
        "setting_id": "setting_items",
    },
    "timeline_event_clues": {
        "timeline_event_id": "timeline_events",
        "clue_id": "clues",
    },
    "outline_item_characters": {
        "outline_item_id": "outline_items",
        "character_id": "characters",
    },
    "outline_item_settings": {
        "outline_item_id": "outline_items",
        "setting_id": "setting_items",
    },
    "outline_item_clues": {
        "outline_item_id": "outline_items",
        "clue_id": "clues",
    },
    "outline_item_timeline_events": {
        "outline_item_id": "outline_items",
        "timeline_event_id": "timeline_events",
    },
}


class SyncApplyService:
    """Applies remote cloud sync changes to the local database."""

    def __init__(self, db: Session):
        self.db = db

    def apply_changes(self, changes: list[dict[str, Any]]) -> dict[str, int]:
        """Apply a list of remote changes to local SQLite.

        Changes are applied in SYNC_APPLY_ORDER for upserts and
        SYNC_DELETE_ORDER for deletes to respect FK constraints.

        For outline_items, a two-phase apply is used to handle
        self-referencing parent_id: first pass applies items whose
        parents already exist, second pass applies the rest.

        Returns a dict with counts: {"applied": N, "skipped": M}.
        """
        # Separate upserts and deletes
        upserts: list[dict[str, Any]] = []
        deletes: list[dict[str, Any]] = []

        for change in changes:
            entity_type = change.get("entity_type", "")
            if entity_type not in SYNC_ENTITY_MODELS:
                logger.warning(
                    "Ignoring unknown entity type in remote change: %s",
                    entity_type,
                )
                continue

            action = change.get("action", "upsert")
            if action == "delete":
                deletes.append(change)
            else:
                upserts.append(change)

        applied = 0
        skipped = 0

        # Apply upserts in dependency order
        for entity_type in SYNC_APPLY_ORDER:
            type_changes = [c for c in upserts if c["entity_type"] == entity_type]

            if entity_type == "outline_items" and len(type_changes) > 1:
                # Two-phase apply for outline_items self-reference
                a, s = self._apply_outline_items_two_phase(type_changes)
                applied += a
                skipped += s
            else:
                for change in type_changes:
                    try:
                        self._apply_upsert(change)
                        applied += 1
                    except ValueError as exc:
                        logger.warning(
                            "Skipped %s/%s — P1 dependency: %s",
                            change.get("entity_type"),
                            change.get("entity_id"),
                            exc,
                        )
                        skipped += 1
                    except IntegrityError as exc:
                        self.db.rollback()
                        logger.warning(
                            "Skipped %s/%s — missing FK dependency: %s",
                            change.get("entity_type"),
                            change.get("entity_id"),
                            exc,
                        )
                        skipped += 1
                    except Exception as exc:
                        logger.error(
                            "Failed to apply upsert for %s/%s: %s",
                            change.get("entity_type"),
                            change.get("entity_id"),
                            exc,
                        )
                        skipped += 1

        # Apply deletes in reverse dependency order
        for entity_type in SYNC_DELETE_ORDER:
            type_changes = [c for c in deletes if c["entity_type"] == entity_type]
            for change in type_changes:
                try:
                    self._apply_delete(change)
                    applied += 1
                except Exception as exc:
                    logger.error(
                        "Failed to apply delete for %s/%s: %s",
                        change.get("entity_type"),
                        change.get("entity_id"),
                        exc,
                    )
                    skipped += 1

        self.db.commit()
        return {"applied": applied, "skipped": skipped}

    def _apply_outline_items_two_phase(
        self, changes: list[dict[str, Any]]
    ) -> tuple[int, int]:
        """Apply outline_items in two phases to handle parent_id self-reference.

        Phase 1: apply items whose parent_id is None or already exists locally.
        Phase 2: apply remaining items (their parents should now exist from phase 1).
        """
        applied = 0
        skipped = 0
        deferred: list[dict[str, Any]] = []

        for change in changes:
            data = change.get("data", {})
            parent_id = data.get("parent_id")

            if parent_id is None:
                # No parent — apply directly
                try:
                    self._apply_upsert(change)
                    applied += 1
                except Exception as exc:
                    logger.error(
                        "Failed to apply outline_item %s: %s",
                        change.get("entity_id"),
                        exc,
                    )
                    skipped += 1
                continue

            # Check if parent already exists locally
            existing_parent = get_entity_by_id(self.db, "outline_items", parent_id)
            if existing_parent is not None:
                try:
                    self._apply_upsert(change)
                    applied += 1
                except Exception as exc:
                    logger.error(
                        "Failed to apply outline_item %s: %s",
                        change.get("entity_id"),
                        exc,
                    )
                    skipped += 1
            else:
                deferred.append(change)

        # Phase 2: apply deferred items
        for change in deferred:
            try:
                self._apply_upsert(change)
                applied += 1
            except IntegrityError as exc:
                self.db.rollback()
                logger.warning(
                    "Skipped outline_item %s — parent %s not found: %s",
                    change.get("entity_id"),
                    change.get("data", {}).get("parent_id"),
                    exc,
                )
                skipped += 1
            except Exception as exc:
                logger.error(
                    "Failed to apply outline_item %s: %s",
                    change.get("entity_id"),
                    exc,
                )
                skipped += 1

        return applied, skipped

    def _apply_upsert(self, change: dict[str, Any]) -> None:
        """Upsert a single entity from remote change data.

        For P1 join entities, validates that parent entities exist and are
        active before creating/updating. Raises ValueError if a parent is
        missing — caller should catch and skip.

        Raises IntegrityError if FK dependencies are missing — caller
        should catch and handle (skip with warning).
        """
        entity_type = change["entity_type"]
        entity_id = change["entity_id"]
        data = change.get("data", {})

        # Validate P1 dependencies before applying
        if entity_type in _P1_DEPENDENCY_MAP:
            if not self._validate_p1_dependencies(entity_type, data):
                raise ValueError(
                    f"P1 dependency missing for {entity_type}/{entity_id}"
                )

        model_cls = SYNC_ENTITY_MODELS[entity_type]
        kwargs = deserialize_entity(data, entity_type)

        existing = get_entity_by_id(self.db, entity_type, entity_id)

        if existing is not None:
            # Update existing entity
            for key, value in kwargs.items():
                if key == "id":
                    continue
                setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            # Clear deleted_at if it was set (undelete)
            if hasattr(existing, "deleted_at"):
                existing.deleted_at = None
        else:
            # For P1 material link tables, check if a soft-deleted row with
            # the same natural key exists and reuse it (PK normalization).
            if entity_type in _P1_DEPENDENCY_MAP:
                revived = self._try_revive_p1_by_natural_key(
                    entity_type, entity_id, kwargs
                )
                if revived is not None:
                    return

            # Create new entity
            if "id" not in kwargs:
                kwargs["id"] = entity_id
            entity = model_cls(**kwargs)
            self.db.add(entity)
            # Flush to detect FK violations early
            self.db.flush()

    def _validate_p1_dependencies(
        self, entity_type: str, data: dict[str, Any]
    ) -> bool:
        """Check that all parent entities referenced by a P1 join row exist
        and are active. Returns True if all dependencies are satisfied."""
        deps = _P1_DEPENDENCY_MAP.get(entity_type, {})
        for field_name, parent_type in deps.items():
            parent_id = data.get(field_name)
            if parent_id is None:
                return False
            parent = get_active_entity(self.db, parent_type, parent_id)
            if parent is None:
                logger.warning(
                    "P1 dependency missing: %s.%s -> %s/%s",
                    entity_type,
                    field_name,
                    parent_type,
                    parent_id,
                )
                return False
        return True

    def _try_revive_p1_by_natural_key(
        self,
        entity_type: str,
        entity_id: str,
        kwargs: dict[str, Any],
    ) -> Any | None:
        """For P1 material link tables with unique natural keys, check if a
        soft-deleted row with the same natural key exists. If so, normalize
        its PK to the remote entity_id, clear deleted_at, and return it."""
        deps = _P1_DEPENDENCY_MAP.get(entity_type, {})
        if not deps:
            return None

        model_cls = SYNC_ENTITY_MODELS[entity_type]
        # Build natural key conditions from the dependency fields
        conditions = []
        for field_name in deps:
            value = kwargs.get(field_name)
            if value is None:
                return None
            conditions.append(getattr(model_cls, field_name) == value)

        from sqlalchemy import select

        statement = select(model_cls).where(*conditions)
        existing = self.db.scalar(statement)

        if existing is None:
            return None

        # Normalize PK to remote entity_id and revive
        existing.id = entity_id
        for key, value in kwargs.items():
            if key == "id":
                continue
            setattr(existing, key, value)
        existing.deleted_at = None
        existing.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        return existing

    def _apply_delete(self, change: dict[str, Any]) -> None:
        """Soft-delete a single entity from remote change data."""
        entity_type = change["entity_type"]
        entity_id = change["entity_id"]

        existing = get_entity_by_id(self.db, entity_type, entity_id)
        if existing is None:
            # Entity doesn't exist locally — nothing to do
            return

        if hasattr(existing, "deleted_at"):
            existing.deleted_at = datetime.now(timezone.utc)
            existing.updated_at = datetime.now(timezone.utc)
        else:
            # Hard delete if model doesn't support soft delete
            self.db.delete(existing)
