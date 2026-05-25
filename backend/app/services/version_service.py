"""Unified version management service.

Provides a project-level version center that unifies chapter versions
(from chapter_versions table) and non-chapter entity versions (from
entity_versions table) behind a single API.
"""

from __future__ import annotations

import difflib
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.character import Character
from app.models.clue import Clue
from app.models.entity_version import EntityVersion
from app.models.knowledge_source import KnowledgeSource
from app.models.outline_item import OutlineItem
from app.models.project import Project
from app.models.setting_item import SettingItem
from app.repositories.chapter_version_repo import ChapterVersionRepository
from app.repositories.entity_version_repo import EntityVersionRepository
from app.schemas.version import (
    CleanupVersionsResponse,
    CreateVersionSnapshotRequest,
    DiffLine,
    RestoreVersionResponse,
    UpdateVersionRequest,
    VersionCompareRequest,
    VersionCompareResponse,
    VersionDetail,
    VersionListItem,
    VersionListResponse,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class VersionProjectNotFoundError(Exception):
    pass


class VersionNotFoundError(Exception):
    pass


class VersionEntityNotFoundError(Exception):
    pass


class VersionRestoreMismatchError(Exception):
    pass


class VersionPinnedError(Exception):
    pass


# ---------------------------------------------------------------------------
# Entity snapshot adapters
# ---------------------------------------------------------------------------


# Fields that can be snapshotted / restored for each entity type
_ENTITY_FIELDS: dict[str, list[str]] = {
    "setting": ["title", "summary", "detail", "tags", "item_type", "canon_status", "importance"],
    "character": [
        "name", "role", "summary", "biography", "appearance",
        "personality", "background", "ability", "motivation",
        "secret", "arc", "notes",
    ],
    "clue": [
        "title", "description", "status", "visibility", "importance",
        "payoff_plan", "actual_payoff", "note",
    ],
    "outline": ["title", "content", "item_type", "status", "importance"],
    "knowledge_source": [
        "title", "source_type", "source_uri", "author",
        "summary", "content", "tags", "credibility",
    ],
}

# Model classes for each entity type
_ENTITY_MODELS: dict[str, type] = {
    "setting": SettingItem,
    "character": Character,
    "clue": Clue,
    "outline": OutlineItem,
    "knowledge_source": KnowledgeSource,
}

# Title field for each entity type (some use 'name' instead of 'title')
_ENTITY_TITLE_FIELD: dict[str, str] = {
    "setting": "title",
    "character": "name",
    "clue": "title",
    "outline": "title",
    "knowledge_source": "title",
}


def _get_entity(model_cls: type, db: Session, entity_id: str):
    """Fetch an entity, returning None if not found or soft-deleted."""
    entity = db.get(model_cls, entity_id)
    if entity is None:
        return None
    if hasattr(entity, "deleted_at") and entity.deleted_at is not None:
        return None
    return entity


def _entity_to_snapshot(entity, entity_type: str) -> dict:
    fields = _ENTITY_FIELDS.get(entity_type, [])
    return {f: getattr(entity, f, None) for f in fields}


def _entity_content_text(entity, entity_type: str) -> str:
    """Extract a human-readable text representation for diff."""
    if entity_type == "setting":
        parts = [
            f"标题: {entity.title}",
            f"摘要: {entity.summary}",
            f"详情: {entity.detail}",
        ]
        if entity.tags:
            parts.append(f"标签: {entity.tags}")
        return "\n\n".join(parts)
    elif entity_type == "character":
        parts = [f"姓名: {entity.name}"]
        for field in ["summary", "biography", "appearance", "personality",
                       "background", "ability", "motivation", "secret", "arc", "notes"]:
            val = getattr(entity, field, "")
            if val:
                parts.append(f"{field}: {val}")
        return "\n\n".join(parts)
    elif entity_type == "clue":
        parts = [
            f"标题: {entity.title}",
            f"描述: {entity.description}",
        ]
        if entity.payoff_plan:
            parts.append(f"回收计划: {entity.payoff_plan}")
        if entity.actual_payoff:
            parts.append(f"实际回收: {entity.actual_payoff}")
        if entity.note:
            parts.append(f"备注: {entity.note}")
        return "\n\n".join(parts)
    elif entity_type == "outline":
        return f"{entity.title}\n\n{entity.content}"
    elif entity_type == "knowledge_source":
        parts = [f"标题: {entity.title}"]
        if entity.summary:
            parts.append(f"摘要: {entity.summary}")
        if entity.content:
            parts.append(entity.content)
        return "\n\n".join(parts)
    return ""


def _count_words(text: str) -> int:
    return len(text.replace(" ", "").replace("\n", ""))


# ---------------------------------------------------------------------------
# Version ref encoding
# ---------------------------------------------------------------------------

def _chapter_ref(version_id: str) -> str:
    return f"chapter_version:{version_id}"


def _entity_ref(version_id: str) -> str:
    return f"entity_version:{version_id}"


def _parse_ref(version_ref: str) -> tuple[str, str]:
    """Return (kind, uuid) from a version ref."""
    if version_ref.startswith("chapter_version:"):
        return "chapter", version_ref[len("chapter_version:"):]
    if version_ref.startswith("entity_version:"):
        return "entity", version_ref[len("entity_version:"):]
    raise VersionNotFoundError()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class VersionService:
    def __init__(self, db: Session):
        self.db = db
        self._chapter_repo = ChapterVersionRepository(db)
        self._entity_repo = EntityVersionRepository(db)

    # -- list --------------------------------------------------------------

    def list_versions(
        self,
        project_id: str,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        source: str | None = None,
        pinned: bool | None = None,
        keyword: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> VersionListResponse:
        self._ensure_project(project_id)
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        items: list[VersionListItem] = []

        # Chapter versions
        if entity_type is None or entity_type == "chapter":
            cv_rows, _ = self._chapter_repo.list_by_project(
                project_id,
                entity_id=entity_id if entity_type == "chapter" else None,
                source=source,
                pinned=pinned,
                keyword=keyword,
                limit=limit,
                offset=0,
            )
            for cv in cv_rows:
                items.append(
                    VersionListItem(
                        version_ref=_chapter_ref(cv.id),
                        entity_type="chapter",
                        entity_id=cv.chapter_id,
                        entity_title=cv.title,
                        source=cv.source,
                        label=cv.label,
                        note=cv.note,
                        is_pinned=cv.is_pinned,
                        word_count=cv.word_count,
                        created_at=cv.created_at,
                    )
                )

        # Entity versions
        if entity_type is None or entity_type != "chapter":
            ev_rows, _ = self._entity_repo.list_by_project(
                project_id,
                entity_type=entity_type if entity_type and entity_type != "chapter" else None,
                entity_id=entity_id if entity_type and entity_type != "chapter" else None,
                source=source,
                pinned=pinned,
                keyword=keyword,
                limit=limit,
                offset=0,
            )
            for ev in ev_rows:
                items.append(
                    VersionListItem(
                        version_ref=_entity_ref(ev.id),
                        entity_type=ev.entity_type,
                        entity_id=ev.entity_id,
                        entity_title=ev.entity_title,
                        source=ev.source,
                        label=ev.label,
                        note=ev.note,
                        is_pinned=ev.is_pinned,
                        word_count=ev.word_count,
                        created_at=ev.created_at,
                    )
                )

        # Sort by created_at descending, then paginate
        items.sort(key=lambda x: x.created_at, reverse=True)
        total = len(items)
        page = items[offset : offset + limit]

        return VersionListResponse(
            project_id=project_id,
            total=total,
            limit=limit,
            offset=offset,
            versions=page,
        )

    # -- detail ------------------------------------------------------------

    def get_version(self, project_id: str, version_ref: str) -> VersionDetail:
        self._ensure_project(project_id)
        kind, vid = _parse_ref(version_ref)

        if kind == "chapter":
            cv = self._chapter_repo.get(vid)
            if cv is None or cv.project_id != project_id:
                raise VersionNotFoundError()
            return VersionDetail(
                version_ref=_chapter_ref(cv.id),
                entity_type="chapter",
                entity_id=cv.chapter_id,
                entity_title=cv.title,
                source=cv.source,
                label=cv.label,
                note=cv.note,
                is_pinned=cv.is_pinned,
                word_count=cv.word_count,
                created_at=cv.created_at,
                content_text=f"{cv.title}\n\n{cv.content}",
                snapshot_json=None,
                metadata=self._safe_json(cv.metadata_json),
            )
        else:
            ev = self._entity_repo.get(vid)
            if ev is None or ev.project_id != project_id:
                raise VersionNotFoundError()
            return VersionDetail(
                version_ref=_entity_ref(ev.id),
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                entity_title=ev.entity_title,
                source=ev.source,
                label=ev.label,
                note=ev.note,
                is_pinned=ev.is_pinned,
                word_count=ev.word_count,
                created_at=ev.created_at,
                content_text=ev.content_text,
                snapshot_json=self._safe_json(ev.snapshot_json),
                metadata=self._safe_json(ev.metadata_json),
            )

    # -- create snapshot ---------------------------------------------------

    def create_snapshot(
        self,
        project_id: str,
        data: CreateVersionSnapshotRequest,
    ) -> VersionListItem:
        self._ensure_project(project_id)

        if data.entity_type == "chapter":
            return self._create_chapter_snapshot(project_id, data)
        return self._create_entity_snapshot(project_id, data)

    # -- update ------------------------------------------------------------

    def update_version(
        self,
        project_id: str,
        version_ref: str,
        data: UpdateVersionRequest,
    ) -> VersionListItem:
        self._ensure_project(project_id)
        kind, vid = _parse_ref(version_ref)

        values = data.model_dump(exclude_unset=True)

        if kind == "chapter":
            cv = self._chapter_repo.get(vid)
            if cv is None or cv.project_id != project_id:
                raise VersionNotFoundError()
            cv = self._chapter_repo.update(cv, values)
            return VersionListItem(
                version_ref=_chapter_ref(cv.id),
                entity_type="chapter",
                entity_id=cv.chapter_id,
                entity_title=cv.title,
                source=cv.source,
                label=cv.label,
                note=cv.note,
                is_pinned=cv.is_pinned,
                word_count=cv.word_count,
                created_at=cv.created_at,
            )
        else:
            ev = self._entity_repo.get(vid)
            if ev is None or ev.project_id != project_id:
                raise VersionNotFoundError()
            ev = self._entity_repo.update(ev, values)
            return VersionListItem(
                version_ref=_entity_ref(ev.id),
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                entity_title=ev.entity_title,
                source=ev.source,
                label=ev.label,
                note=ev.note,
                is_pinned=ev.is_pinned,
                word_count=ev.word_count,
                created_at=ev.created_at,
            )

    # -- delete ------------------------------------------------------------

    def delete_version(self, project_id: str, version_ref: str) -> None:
        self._ensure_project(project_id)
        kind, vid = _parse_ref(version_ref)

        if kind == "chapter":
            cv = self._chapter_repo.get(vid)
            if cv is None or cv.project_id != project_id:
                raise VersionNotFoundError()
            if cv.is_pinned:
                raise VersionPinnedError()
            self._chapter_repo.soft_delete(cv)
        else:
            ev = self._entity_repo.get(vid)
            if ev is None or ev.project_id != project_id:
                raise VersionNotFoundError()
            if ev.is_pinned:
                raise VersionPinnedError()
            self._entity_repo.soft_delete(ev)

    # -- compare -----------------------------------------------------------

    def compare(
        self,
        project_id: str,
        data: VersionCompareRequest,
    ) -> VersionCompareResponse:
        self._ensure_project(project_id)

        detail_a = self.get_version(project_id, data.version_ref_a)

        if data.version_ref_b:
            detail_b = self.get_version(project_id, data.version_ref_b)
            text_b = detail_b.content_text
            title_b = detail_b.entity_title
        else:
            # Compare with current entity content
            text_b, title_b = self._get_current_content(
                project_id, detail_a.entity_type, detail_a.entity_id
            )

        diff = self._compute_diff(detail_a.content_text, text_b)
        return VersionCompareResponse(
            version_ref_a=data.version_ref_a,
            version_ref_b=data.version_ref_b,
            title_a=detail_a.entity_title,
            title_b=title_b,
            diff=diff,
        )

    # -- restore -----------------------------------------------------------

    def restore(
        self,
        project_id: str,
        version_ref: str,
    ) -> RestoreVersionResponse:
        self._ensure_project(project_id)
        kind, vid = _parse_ref(version_ref)

        if kind == "chapter":
            return self._restore_chapter(project_id, vid)
        return self._restore_entity(project_id, vid)

    # -- cleanup -----------------------------------------------------------

    def cleanup(
        self,
        project_id: str,
        *,
        keep_days: int = 30,
    ) -> CleanupVersionsResponse:
        self._ensure_project(project_id)
        count = self._chapter_repo.cleanup_unpinned_autosave(
            project_id, keep_days=keep_days
        )
        return CleanupVersionsResponse(
            deleted_count=count,
            message=f"已清理 {count} 个旧自动保存版本",
        )

    # ------------------------------------------------------------------
    # Private: chapter operations
    # ------------------------------------------------------------------

    def _create_chapter_snapshot(
        self, project_id: str, data: CreateVersionSnapshotRequest
    ) -> VersionListItem:
        chapter = self.db.get(Chapter, data.entity_id)
        if chapter is None or chapter.deleted_at is not None:
            raise VersionEntityNotFoundError()
        if chapter.project_id != project_id:
            raise VersionEntityNotFoundError()

        from app.models.chapter_version import ChapterVersion

        cv = ChapterVersion(
            id=str(uuid4()),
            chapter_id=chapter.id,
            project_id=project_id,
            title=chapter.title,
            content=chapter.content,
            word_count=chapter.word_count,
            source="manual",
            label=data.label,
            note=data.note,
        )
        cv = self._chapter_repo.create(cv)
        return VersionListItem(
            version_ref=_chapter_ref(cv.id),
            entity_type="chapter",
            entity_id=cv.chapter_id,
            entity_title=cv.title,
            source=cv.source,
            label=cv.label,
            note=cv.note,
            is_pinned=cv.is_pinned,
            word_count=cv.word_count,
            created_at=cv.created_at,
        )

    def _restore_chapter(
        self, project_id: str, version_id: str
    ) -> RestoreVersionResponse:
        from app.models.chapter_version import ChapterVersion

        cv = self._chapter_repo.get(version_id)
        if cv is None or cv.project_id != project_id:
            raise VersionNotFoundError()

        chapter = self.db.get(Chapter, cv.chapter_id)
        if chapter is None or chapter.deleted_at is not None:
            raise VersionEntityNotFoundError()

        try:
            # before_restore snapshot
            before = ChapterVersion(
                id=str(uuid4()),
                chapter_id=chapter.id,
                project_id=project_id,
                title=chapter.title,
                content=chapter.content,
                word_count=chapter.word_count,
                source="before_restore",
                note="恢复版本前自动备份",
            )
            self._chapter_repo.create(before, commit=False)
            before_ref = _chapter_ref(before.id)

            # Restore
            from app.services.chapter_service import calculate_word_count

            chapter.title = cv.title
            chapter.content = cv.content
            chapter.word_count = calculate_word_count(cv.content)
            chapter.updated_at = datetime.now(timezone.utc)
            chapter.version = (chapter.version or 0) + 1

            # restore snapshot
            after = ChapterVersion(
                id=str(uuid4()),
                chapter_id=chapter.id,
                project_id=project_id,
                title=chapter.title,
                content=chapter.content,
                word_count=chapter.word_count,
                source="restore",
                note=f"从版本 {cv.id} 恢复",
            )
            self._chapter_repo.create(after, commit=False)
            self.db.commit()

            return RestoreVersionResponse(
                version_ref=_chapter_ref(cv.id),
                entity_type="chapter",
                entity_id=cv.chapter_id,
                before_restore_ref=before_ref,
                message="章节已恢复，恢复前快照已创建",
            )
        except Exception:
            self.db.rollback()
            raise

    # ------------------------------------------------------------------
    # Private: entity operations
    # ------------------------------------------------------------------

    def _create_entity_snapshot(
        self, project_id: str, data: CreateVersionSnapshotRequest
    ) -> VersionListItem:
        model_cls = _ENTITY_MODELS.get(data.entity_type)
        if model_cls is None:
            raise VersionEntityNotFoundError()

        entity = _get_entity(model_cls, self.db, data.entity_id)
        if entity is None:
            raise VersionEntityNotFoundError()
        if getattr(entity, "project_id", None) != project_id:
            raise VersionEntityNotFoundError()

        title_field = _ENTITY_TITLE_FIELD.get(data.entity_type, "title")
        entity_title = getattr(entity, title_field, "")
        snapshot = _entity_to_snapshot(entity, data.entity_type)
        content_text = _entity_content_text(entity, data.entity_type)

        ev = EntityVersion(
            id=str(uuid4()),
            project_id=project_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            entity_title=entity_title,
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            content_text=content_text,
            word_count=_count_words(content_text),
            source="manual",
            label=data.label,
            note=data.note,
        )
        ev = self._entity_repo.create(ev)
        return VersionListItem(
            version_ref=_entity_ref(ev.id),
            entity_type=ev.entity_type,
            entity_id=ev.entity_id,
            entity_title=ev.entity_title,
            source=ev.source,
            label=ev.label,
            note=ev.note,
            is_pinned=ev.is_pinned,
            word_count=ev.word_count,
            created_at=ev.created_at,
        )

    def _restore_entity(
        self, project_id: str, version_id: str
    ) -> RestoreVersionResponse:
        ev = self._entity_repo.get(version_id)
        if ev is None or ev.project_id != project_id:
            raise VersionNotFoundError()

        model_cls = _ENTITY_MODELS.get(ev.entity_type)
        if model_cls is None:
            raise VersionEntityNotFoundError()

        entity = _get_entity(model_cls, self.db, ev.entity_id)
        if entity is None:
            raise VersionEntityNotFoundError()

        try:
            # before_restore snapshot
            title_field = _ENTITY_TITLE_FIELD.get(ev.entity_type, "title")
            current_title = getattr(entity, title_field, "")
            current_snapshot = _entity_to_snapshot(entity, ev.entity_type)
            current_content = _entity_content_text(entity, ev.entity_type)

            before = EntityVersion(
                id=str(uuid4()),
                project_id=project_id,
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                entity_title=current_title,
                snapshot_json=json.dumps(current_snapshot, ensure_ascii=False),
                content_text=current_content,
                word_count=_count_words(current_content),
                source="before_restore",
                note="恢复版本前自动备份",
            )
            self._entity_repo.create(before, commit=False)
            before_ref = _entity_ref(before.id)

            # Restore allowed fields
            snapshot_data = json.loads(ev.snapshot_json) if ev.snapshot_json else {}
            allowed_fields = _ENTITY_FIELDS.get(ev.entity_type, [])
            for field in allowed_fields:
                if field in snapshot_data:
                    setattr(entity, field, snapshot_data[field])

            entity.updated_at = datetime.now(timezone.utc)
            entity.version = (getattr(entity, "version", 0) or 0) + 1

            # after snapshot
            restored_snapshot = _entity_to_snapshot(entity, ev.entity_type)
            restored_content = _entity_content_text(entity, ev.entity_type)
            after = EntityVersion(
                id=str(uuid4()),
                project_id=project_id,
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                entity_title=getattr(entity, title_field, ""),
                snapshot_json=json.dumps(restored_snapshot, ensure_ascii=False),
                content_text=restored_content,
                word_count=_count_words(restored_content),
                source="restore",
                note=f"从版本 {ev.id} 恢复",
            )
            self._entity_repo.create(after, commit=False)
            self.db.commit()

            return RestoreVersionResponse(
                version_ref=_entity_ref(ev.id),
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                before_restore_ref=before_ref,
                message="实体已恢复，恢复前快照已创建",
            )
        except Exception:
            self.db.rollback()
            raise

    # ------------------------------------------------------------------
    # Private: helpers
    # ------------------------------------------------------------------

    def _ensure_project(self, project_id: str) -> None:
        project = self.db.get(Project, project_id)
        if project is None or project.deleted_at is not None:
            raise VersionProjectNotFoundError()

    def _get_current_content(
        self, project_id: str, entity_type: str, entity_id: str
    ) -> tuple[str, str]:
        """Get current entity content text and title for comparison."""
        if entity_type == "chapter":
            chapter = self.db.get(Chapter, entity_id)
            if chapter and chapter.deleted_at is None:
                return f"{chapter.title}\n\n{chapter.content}", chapter.title
            return "", "(未找到)"

        model_cls = _ENTITY_MODELS.get(entity_type)
        if model_cls is None:
            return "", "(未找到)"

        entity = _get_entity(model_cls, self.db, entity_id)
        if entity is None:
            return "", "(未找到)"

        title_field = _ENTITY_TITLE_FIELD.get(entity_type, "title")
        title = getattr(entity, title_field, "")
        content = _entity_content_text(entity, entity_type)
        return content, title

    @staticmethod
    def _compute_diff(old_text: str, new_text: str) -> list[DiffLine]:
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        result: list[DiffLine] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for line in old_lines[i1:i2]:
                    result.append(DiffLine(tag="equal", old_text=line, new_text=line))
            elif tag == "delete":
                for line in old_lines[i1:i2]:
                    result.append(DiffLine(tag="delete", old_text=line))
            elif tag == "insert":
                for line in new_lines[j1:j2]:
                    result.append(DiffLine(tag="insert", new_text=line))
            elif tag == "replace":
                for line in old_lines[i1:i2]:
                    result.append(DiffLine(tag="delete", old_text=line))
                for line in new_lines[j1:j2]:
                    result.append(DiffLine(tag="insert", new_text=line))

        return result

    @staticmethod
    def _safe_json(value: str | None) -> dict | None:
        if not value or value == "{}":
            return None
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None
