"""Repository for FTS5 full-text search queries.

All FTS5 raw SQL is encapsulated here.  Business services never execute
FTS queries directly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.search_fts import FTS_TABLE


# ---------------------------------------------------------------------------
# Result data class (internal to the repository layer)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FtsSearchRow:
    entity_type: str
    entity_id: str
    title: str
    snippet: str
    score: float
    updated_at: str
    metadata_json: str


# ---------------------------------------------------------------------------
# Entity types that can be filtered
# ---------------------------------------------------------------------------

VALID_ENTITY_TYPES = frozenset(
    {"chapter", "setting", "character", "clue", "outline", "knowledge", "timeline", "graph"}
)

# Minimum query length for FTS MATCH.  Trigram tokenizer needs >= 3 chars.
# Shorter queries fall back to LIKE.
_MIN_FTS_QUERY_LEN = 3


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class SearchIndexRepository:
    def __init__(self, db: Session):
        self.db = db

    # -- search ------------------------------------------------------------

    def search(
        self,
        project_id: str,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[FtsSearchRow], int]:
        """Search the FTS5 index and return matching rows plus total count.

        For queries shorter than *_MIN_FTS_QUERY_LEN* a LIKE fallback is used
        so that single-character searches still return results.
        """
        keyword = query.strip()
        if not keyword:
            return [], 0

        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        type_filter = self._normalise_types(entity_types)

        if len(keyword) < _MIN_FTS_QUERY_LEN:
            return self._search_like(project_id, keyword, type_filter, limit, offset)

        return self._search_fts(project_id, keyword, type_filter, limit, offset)

    # -- rebuild / delete --------------------------------------------------

    def rebuild_project(self, project_id: str) -> int:
        """Delete and re-index all documents for a single project."""
        conn = self.db.connection()
        # Delete existing index rows for this project
        conn.execute(
            text(f"DELETE FROM {FTS_TABLE} WHERE project_id = :pid"),
            {"pid": project_id},
        )

        count = 0
        count += self._backfill_chapters(conn, project_id)
        count += self._backfill_settings(conn, project_id)
        count += self._backfill_characters(conn, project_id)
        count += self._backfill_clues(conn, project_id)
        count += self._backfill_outlines(conn, project_id)
        count += self._backfill_knowledge(conn, project_id)
        count += self._backfill_timeline(conn, project_id)
        count += self._backfill_graph(conn, project_id)

        self.db.commit()
        return count

    def delete_project(self, project_id: str) -> None:
        """Remove all FTS index entries for a project."""
        conn = self.db.connection()
        conn.execute(
            text(f"DELETE FROM {FTS_TABLE} WHERE project_id = :pid"),
            {"pid": project_id},
        )
        self.db.commit()

    # ------------------------------------------------------------------
    # Private: FTS search
    # ------------------------------------------------------------------

    def _search_fts(
        self,
        project_id: str,
        keyword: str,
        type_filter: list[str] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[FtsSearchRow], int]:
        match_expr = self._build_match_expr(keyword)

        type_clause = ""
        type_params: dict[str, str] = {}
        if type_filter:
            placeholders = []
            for i, t in enumerate(type_filter):
                key = f"t{i}"
                placeholders.append(f":{key}")
                type_params[key] = t
            type_clause = f"AND entity_type IN ({', '.join(placeholders)})"

        params: dict = {"pid": project_id, "match": match_expr, **type_params}

        # Count
        count_sql = (
            f"SELECT COUNT(*) FROM {FTS_TABLE}"
            " WHERE project_id = :pid"
            f" AND {FTS_TABLE} MATCH :match"
            f" {type_clause}"
        )
        total = self.db.execute(text(count_sql), params).scalar() or 0

        # Results – bm25 with title boost (col 3=title w=10, col 4=body w=1, col 5=tags w=1)
        result_sql = (
            f"SELECT entity_type, entity_id, title,"
            f"  snippet({FTS_TABLE}, 4, '>>>', '<<<', '...', 64) AS snippet,"
            f"  bm25({FTS_TABLE}, 0.0, 0.0, 0.0, 10.0, 1.0, 1.0, 0.0, 0.0) * -1 AS score,"
            "  updated_at, metadata_json"
            f" FROM {FTS_TABLE}"
            " WHERE project_id = :pid"
            f" AND {FTS_TABLE} MATCH :match"
            f" {type_clause}"
            " ORDER BY score DESC"
            f" LIMIT :lim OFFSET :off"
        )
        params["lim"] = limit
        params["off"] = offset

        rows = self.db.execute(text(result_sql), params).all()
        results = [
            FtsSearchRow(
                entity_type=r[0],
                entity_id=r[1],
                title=r[2],
                snippet=r[3] or "",
                score=float(r[4]) if r[4] else 0.0,
                updated_at=r[5] or "",
                metadata_json=r[6] or "{}",
            )
            for r in rows
        ]
        return results, total

    # ------------------------------------------------------------------
    # Private: LIKE fallback for very short queries
    # ------------------------------------------------------------------

    def _search_like(
        self,
        project_id: str,
        keyword: str,
        type_filter: list[str] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[FtsSearchRow], int]:
        like_pattern = f"%{self._escape_like(keyword)}%"

        type_clause = ""
        type_params: dict[str, str] = {}
        if type_filter:
            placeholders = []
            for i, t in enumerate(type_filter):
                key = f"t{i}"
                placeholders.append(f":{key}")
                type_params[key] = t
            type_clause = f"AND entity_type IN ({', '.join(placeholders)})"

        params: dict = {
            "pid": project_id,
            "pat": like_pattern,
            **type_params,
        }

        count_sql = (
            f"SELECT COUNT(*) FROM {FTS_TABLE}"
            " WHERE project_id = :pid"
            " AND (title LIKE :pat ESCAPE '\\' OR body LIKE :pat ESCAPE '\\')"
            f" {type_clause}"
        )
        total = self.db.execute(text(count_sql), params).scalar() or 0

        result_sql = (
            f"SELECT entity_type, entity_id, title,"
            f"  snippet({FTS_TABLE}, 4, '>>>', '<<<', '...', 64),"
            "  0.0 AS score,"
            "  updated_at, metadata_json"
            f" FROM {FTS_TABLE}"
            " WHERE project_id = :pid"
            " AND (title LIKE :pat ESCAPE '\\' OR body LIKE :pat ESCAPE '\\')"
            f" {type_clause}"
            " ORDER BY updated_at DESC"
            f" LIMIT :lim OFFSET :off"
        )
        params["lim"] = limit
        params["off"] = offset

        rows = self.db.execute(text(result_sql), params).all()
        results = [
            FtsSearchRow(
                entity_type=r[0],
                entity_id=r[1],
                title=r[2],
                snippet=r[3] or "",
                score=0.0,
                updated_at=r[5] or "",
                metadata_json=r[6] or "{}",
            )
            for r in rows
        ]
        return results, total

    # ------------------------------------------------------------------
    # Private: helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_match_expr(keyword: str) -> str:
        """Build a safe FTS5 MATCH expression from user input.

        Wraps the keyword in double quotes for phrase matching and escapes
        embedded double quotes.
        """
        sanitised = re.sub(r'[\x00-\x1f"]', "", keyword)
        return f'"{sanitised}"'

    @staticmethod
    def _normalise_types(types: list[str] | None) -> list[str] | None:
        if not types:
            return None
        valid = [t for t in types if t in VALID_ENTITY_TYPES]
        return valid or None

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    # ------------------------------------------------------------------
    # Private: per-entity backfill helpers (used by rebuild_project)
    # ------------------------------------------------------------------

    @staticmethod
    def _backfill_chapters(conn, project_id: str) -> int:
        result = conn.execute(
            text(
                f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
                "  title, body, tags, metadata_json, updated_at)"
                " SELECT project_id, 'chapter', id,"
                "  title, COALESCE(content, ''),"
                "  '', '{}',"
                "  COALESCE(strftime('%s', updated_at), '0')"
                " FROM chapters WHERE deleted_at IS NULL AND project_id = :pid"
            ),
            {"pid": project_id},
        )
        return result.rowcount or 0

    @staticmethod
    def _backfill_settings(conn, project_id: str) -> int:
        result = conn.execute(
            text(
                f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
                "  title, body, tags, metadata_json, updated_at)"
                " SELECT project_id, 'setting', id,"
                "  title,"
                "  CASE WHEN node_kind = 'folder' THEN ''"
                "    ELSE COALESCE(summary, '') || ' ' || COALESCE(detail, '') END,"
                "  COALESCE(tags, ''), '{}',"
                "  COALESCE(strftime('%s', updated_at), '0')"
                " FROM setting_items WHERE deleted_at IS NULL AND project_id = :pid"
            ),
            {"pid": project_id},
        )
        return result.rowcount or 0

    @staticmethod
    def _backfill_characters(conn, project_id: str) -> int:
        result = conn.execute(
            text(
                f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
                "  title, body, tags, metadata_json, updated_at)"
                " SELECT project_id, 'character', id,"
                "  name,"
                "  COALESCE(summary, '') || ' ' || COALESCE(biography, '')"
                "  || ' ' || COALESCE(appearance, '') || ' ' || COALESCE(personality, '')"
                "  || ' ' || COALESCE(background, '') || ' ' || COALESCE(ability, '')"
                "  || ' ' || COALESCE(motivation, '') || ' ' || COALESCE(secret, '')"
                "  || ' ' || COALESCE(arc, '') || ' ' || COALESCE(notes, ''),"
                "  '', '{}',"
                "  COALESCE(strftime('%s', updated_at), '0')"
                " FROM characters WHERE deleted_at IS NULL AND project_id = :pid"
            ),
            {"pid": project_id},
        )
        return result.rowcount or 0

    @staticmethod
    def _backfill_clues(conn, project_id: str) -> int:
        result = conn.execute(
            text(
                f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
                "  title, body, tags, metadata_json, updated_at)"
                " SELECT project_id, 'clue', id,"
                "  title,"
                "  COALESCE(description, '') || ' ' || COALESCE(note, '')"
                "  || ' ' || COALESCE(payoff_plan, '') || ' ' || COALESCE(actual_payoff, ''),"
                "  '', '{}',"
                "  COALESCE(strftime('%s', updated_at), '0')"
                " FROM clues WHERE deleted_at IS NULL AND project_id = :pid"
            ),
            {"pid": project_id},
        )
        return result.rowcount or 0

    @staticmethod
    def _backfill_outlines(conn, project_id: str) -> int:
        result = conn.execute(
            text(
                f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
                "  title, body, tags, metadata_json, updated_at)"
                " SELECT project_id, 'outline', id,"
                "  title, COALESCE(content, ''),"
                "  '', '{}',"
                "  COALESCE(strftime('%s', updated_at), '0')"
                " FROM outline_items WHERE deleted_at IS NULL AND project_id = :pid"
            ),
            {"pid": project_id},
        )
        return result.rowcount or 0

    @staticmethod
    def _backfill_knowledge(conn, project_id: str) -> int:
        result = conn.execute(
            text(
                f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
                "  title, body, tags, metadata_json, updated_at)"
                " SELECT project_id, 'knowledge', id,"
                "  COALESCE(heading, ''), COALESCE(content, ''),"
                "  '', json_object('source_id', source_id),"
                "  COALESCE(strftime('%s', updated_at), '0')"
                " FROM knowledge_chunks WHERE deleted_at IS NULL AND project_id = :pid"
            ),
            {"pid": project_id},
        )
        return result.rowcount or 0

    @staticmethod
    def _backfill_timeline(conn, project_id: str) -> int:
        result = conn.execute(
            text(
                f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
                "  title, body, tags, metadata_json, updated_at)"
                " SELECT project_id, 'timeline', id,"
                "  title,"
                "  COALESCE(description, '') || ' ' || COALESCE(note, ''),"
                "  '', '{}',"
                "  COALESCE(strftime('%s', updated_at), '0')"
                " FROM timeline_events WHERE deleted_at IS NULL AND project_id = :pid"
            ),
            {"pid": project_id},
        )
        return result.rowcount or 0

    @staticmethod
    def _backfill_graph(conn, project_id: str) -> int:
        result = conn.execute(
            text(
                f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
                "  title, body, tags, metadata_json, updated_at)"
                " SELECT project_id, 'graph', id,"
                "  title, COALESCE(summary, ''),"
                "  '', '{}',"
                "  COALESCE(strftime('%s', updated_at), '0')"
                " FROM graph_nodes WHERE deleted_at IS NULL AND project_id = :pid"
            ),
            {"pid": project_id},
        )
        return result.rowcount or 0
