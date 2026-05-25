"""SQLite FTS5 full-text search infrastructure.

Provides capability detection, FTS5 virtual table DDL, triggers for
automatic index maintenance, and rebuild helpers.  All FTS5 raw SQL is
centralised here so that business services and repositories never touch
FTS internals directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


# ---------------------------------------------------------------------------
# Capability detection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SearchFtsCapabilities:
    supports_fts5: bool
    supports_trigram: bool
    sqlite_version: str
    tokenizer: str  # 'trigram' | 'unicode61'


def detect_fts5_support(connection: Connection) -> SearchFtsCapabilities:
    """Detect FTS5 and trigram tokenizer support on the current connection."""
    sqlite_version = str(
        connection.execute(text("SELECT sqlite_version()")).scalar()
    )

    supports_fts5 = True
    supports_trigram = True

    try:
        connection.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe "
                "USING fts5(x, tokenize='unicode61')"
            )
        )
        connection.execute(text("DROP TABLE IF EXISTS _fts5_probe"))
    except Exception:
        supports_fts5 = False

    if supports_fts5:
        try:
            connection.execute(
                text(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS _trigram_probe "
                    "USING fts5(x, tokenize='trigram')"
                )
            )
            connection.execute(text("DROP TABLE IF EXISTS _trigram_probe"))
        except Exception:
            supports_trigram = False

    tokenizer = "trigram" if supports_trigram else "unicode61"
    return SearchFtsCapabilities(
        supports_fts5=supports_fts5,
        supports_trigram=supports_trigram,
        sqlite_version=sqlite_version,
        tokenizer=tokenizer,
    )


# ---------------------------------------------------------------------------
# FTS5 virtual table name (constant used across the codebase)
# ---------------------------------------------------------------------------

FTS_TABLE = "search_documents_fts"


# ---------------------------------------------------------------------------
# Schema creation & rebuild
# ---------------------------------------------------------------------------


def ensure_search_fts_schema(engine: Engine) -> SearchFtsCapabilities:
    """Create (or recreate) the FTS5 virtual table, triggers and backfill.

    This function is idempotent and safe to call on every application start.
    """
    with engine.begin() as conn:
        caps = detect_fts5_support(conn)
        if not caps.supports_fts5:
            return caps

        _create_fts_table(conn, caps.tokenizer)
        _create_fts_triggers(conn, caps.tokenizer)
        _backfill_fts_index(conn, caps.tokenizer)

    return caps


def _create_fts_table(conn: Connection, tokenizer: str) -> None:
    """Drop and recreate the FTS5 table so schema changes are always applied."""
    conn.execute(text(f"DROP TABLE IF EXISTS {FTS_TABLE}"))
    conn.execute(
        text(
            f"CREATE VIRTUAL TABLE {FTS_TABLE} USING fts5("
            "  project_id UNINDEXED,"
            "  entity_type UNINDEXED,"
            "  entity_id UNINDEXED,"
            "  title,"
            "  body,"
            "  tags,"
            "  metadata_json UNINDEXED,"
            "  updated_at UNINDEXED,"
            f"  tokenize = '{tokenizer}'"
            ")"
        )
    )


# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------


def _create_fts_triggers(conn: Connection, tokenizer: str) -> None:  # noqa: ARG001
    """Drop and recreate all FTS maintenance triggers."""
    # -- chapters ----------------------------------------------------------
    _drop_triggers(conn, "chapters")
    conn.execute(
        text(
            "CREATE TRIGGER chapters_fts_ai AFTER INSERT ON chapters"
            " WHEN NEW.deleted_at IS NULL BEGIN"
            f"  INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  VALUES(NEW.project_id, 'chapter', NEW.id,"
            "    NEW.title, COALESCE(NEW.content, ''),"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0'));"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER chapters_fts_au AFTER UPDATE ON chapters BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'chapter' AND entity_id = OLD.id"
            "    AND title = OLD.title"
            "    AND body = COALESCE(OLD.content, '');"
            "  INSERT INTO"
            f"    {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  SELECT NEW.project_id, 'chapter', NEW.id,"
            "    NEW.title, COALESCE(NEW.content, ''),"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0')"
            "  WHERE NEW.deleted_at IS NULL;"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER chapters_fts_ad AFTER DELETE ON chapters BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'chapter' AND entity_id = OLD.id"
            "    AND title = OLD.title"
            "    AND body = COALESCE(OLD.content, '');"
            " END"
        )
    )

    # -- setting_items (folders index title only) --------------------------
    _drop_triggers(conn, "setting_items")
    conn.execute(
        text(
            "CREATE TRIGGER setting_items_fts_ai AFTER INSERT ON setting_items"
            " WHEN NEW.deleted_at IS NULL BEGIN"
            f"  INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  VALUES(NEW.project_id, 'setting', NEW.id,"
            "    NEW.title,"
            "    CASE WHEN NEW.node_kind = 'folder' THEN ''"
            "      ELSE COALESCE(NEW.summary, '') || ' '"
            "        || COALESCE(NEW.detail, '') END,"
            "    COALESCE(NEW.tags, ''), '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0'));"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER setting_items_fts_au AFTER UPDATE ON setting_items BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'setting' AND entity_id = OLD.id"
            "    AND title = OLD.title"
            "    AND body = CASE WHEN OLD.node_kind = 'folder' THEN ''"
            "      ELSE COALESCE(OLD.summary, '') || ' '"
            "        || COALESCE(OLD.detail, '') END;"
            "  INSERT INTO"
            f"    {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  SELECT NEW.project_id, 'setting', NEW.id,"
            "    NEW.title,"
            "    CASE WHEN NEW.node_kind = 'folder' THEN ''"
            "      ELSE COALESCE(NEW.summary, '') || ' '"
            "        || COALESCE(NEW.detail, '') END,"
            "    COALESCE(NEW.tags, ''), '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0')"
            "  WHERE NEW.deleted_at IS NULL;"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER setting_items_fts_ad AFTER DELETE ON setting_items BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'setting' AND entity_id = OLD.id"
            "    AND title = OLD.title"
            "    AND body = CASE WHEN OLD.node_kind = 'folder' THEN ''"
            "      ELSE COALESCE(OLD.summary, '') || ' '"
            "        || COALESCE(OLD.detail, '') END;"
            " END"
        )
    )

    # -- characters --------------------------------------------------------
    _drop_triggers(conn, "characters")
    _char_body = (
        "COALESCE(NEW.summary, '') || ' '"
        "|| COALESCE(NEW.biography, '') || ' '"
        "|| COALESCE(NEW.appearance, '') || ' '"
        "|| COALESCE(NEW.personality, '') || ' '"
        "|| COALESCE(NEW.background, '') || ' '"
        "|| COALESCE(NEW.ability, '') || ' '"
        "|| COALESCE(NEW.motivation, '') || ' '"
        "|| COALESCE(NEW.secret, '') || ' '"
        "|| COALESCE(NEW.arc, '') || ' '"
        "|| COALESCE(NEW.notes, '')"
    )
    _char_body_old = _char_body.replace("NEW.", "OLD.")
    conn.execute(
        text(
            "CREATE TRIGGER characters_fts_ai AFTER INSERT ON characters"
            " WHEN NEW.deleted_at IS NULL BEGIN"
            f"  INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  VALUES(NEW.project_id, 'character', NEW.id,"
            f"    NEW.name, {_char_body},"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0'));"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER characters_fts_au AFTER UPDATE ON characters BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'character' AND entity_id = OLD.id"
            f"    AND title = OLD.name AND body = {_char_body_old};"
            "  INSERT INTO"
            f"    {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  SELECT NEW.project_id, 'character', NEW.id,"
            f"    NEW.name, {_char_body},"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0')"
            "  WHERE NEW.deleted_at IS NULL;"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER characters_fts_ad AFTER DELETE ON characters BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'character' AND entity_id = OLD.id"
            f"    AND title = OLD.name AND body = {_char_body_old};"
            " END"
        )
    )

    # -- clues -------------------------------------------------------------
    _drop_triggers(conn, "clues")
    _clue_body = (
        "COALESCE(NEW.description, '') || ' '"
        "|| COALESCE(NEW.note, '') || ' '"
        "|| COALESCE(NEW.payoff_plan, '') || ' '"
        "|| COALESCE(NEW.actual_payoff, '')"
    )
    _clue_body_old = _clue_body.replace("NEW.", "OLD.")
    conn.execute(
        text(
            "CREATE TRIGGER clues_fts_ai AFTER INSERT ON clues"
            " WHEN NEW.deleted_at IS NULL BEGIN"
            f"  INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  VALUES(NEW.project_id, 'clue', NEW.id,"
            f"    NEW.title, {_clue_body},"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0'));"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER clues_fts_au AFTER UPDATE ON clues BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'clue' AND entity_id = OLD.id"
            f"    AND title = OLD.title AND body = {_clue_body_old};"
            "  INSERT INTO"
            f"    {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  SELECT NEW.project_id, 'clue', NEW.id,"
            f"    NEW.title, {_clue_body},"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0')"
            "  WHERE NEW.deleted_at IS NULL;"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER clues_fts_ad AFTER DELETE ON clues BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'clue' AND entity_id = OLD.id"
            f"    AND title = OLD.title AND body = {_clue_body_old};"
            " END"
        )
    )

    # -- outline_items -----------------------------------------------------
    _drop_triggers(conn, "outline_items")
    conn.execute(
        text(
            "CREATE TRIGGER outline_items_fts_ai AFTER INSERT ON outline_items"
            " WHEN NEW.deleted_at IS NULL BEGIN"
            f"  INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  VALUES(NEW.project_id, 'outline', NEW.id,"
            "    NEW.title, COALESCE(NEW.content, ''),"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0'));"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER outline_items_fts_au AFTER UPDATE ON outline_items BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'outline' AND entity_id = OLD.id"
            "    AND title = OLD.title"
            "    AND body = COALESCE(OLD.content, '');"
            "  INSERT INTO"
            f"    {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  SELECT NEW.project_id, 'outline', NEW.id,"
            "    NEW.title, COALESCE(NEW.content, ''),"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0')"
            "  WHERE NEW.deleted_at IS NULL;"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER outline_items_fts_ad AFTER DELETE ON outline_items BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'outline' AND entity_id = OLD.id"
            "    AND title = OLD.title"
            "    AND body = COALESCE(OLD.content, '');"
            " END"
        )
    )

    # -- knowledge_chunks --------------------------------------------------
    _drop_triggers(conn, "knowledge_chunks")
    conn.execute(
        text(
            "CREATE TRIGGER knowledge_chunks_fts_ai AFTER INSERT ON knowledge_chunks"
            " WHEN NEW.deleted_at IS NULL BEGIN"
            f"  INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  VALUES(NEW.project_id, 'knowledge', NEW.id,"
            "    COALESCE(NEW.heading, ''), COALESCE(NEW.content, ''),"
            "    '', json_object('source_id', NEW.source_id),"
            "    COALESCE(strftime('%s', NEW.updated_at), '0'));"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER knowledge_chunks_fts_au AFTER UPDATE ON knowledge_chunks BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'knowledge' AND entity_id = OLD.id"
            "    AND title = COALESCE(OLD.heading, '')"
            "    AND body = COALESCE(OLD.content, '');"
            "  INSERT INTO"
            f"    {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  SELECT NEW.project_id, 'knowledge', NEW.id,"
            "    COALESCE(NEW.heading, ''), COALESCE(NEW.content, ''),"
            "    '', json_object('source_id', NEW.source_id),"
            "    COALESCE(strftime('%s', NEW.updated_at), '0')"
            "  WHERE NEW.deleted_at IS NULL;"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER knowledge_chunks_fts_ad AFTER DELETE ON knowledge_chunks BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'knowledge' AND entity_id = OLD.id"
            "    AND title = COALESCE(OLD.heading, '')"
            "    AND body = COALESCE(OLD.content, '');"
            " END"
        )
    )

    # -- timeline_events ---------------------------------------------------
    _drop_triggers(conn, "timeline_events")
    conn.execute(
        text(
            "CREATE TRIGGER timeline_events_fts_ai AFTER INSERT ON timeline_events"
            " WHEN NEW.deleted_at IS NULL BEGIN"
            f"  INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  VALUES(NEW.project_id, 'timeline', NEW.id,"
            "    NEW.title,"
            "    COALESCE(NEW.description, '') || ' ' || COALESCE(NEW.note, ''),"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0'));"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER timeline_events_fts_au AFTER UPDATE ON timeline_events BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'timeline' AND entity_id = OLD.id"
            "    AND title = OLD.title"
            "    AND body = COALESCE(OLD.description, '') || ' ' || COALESCE(OLD.note, '');"
            "  INSERT INTO"
            f"    {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  SELECT NEW.project_id, 'timeline', NEW.id,"
            "    NEW.title,"
            "    COALESCE(NEW.description, '') || ' ' || COALESCE(NEW.note, ''),"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0')"
            "  WHERE NEW.deleted_at IS NULL;"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER timeline_events_fts_ad AFTER DELETE ON timeline_events BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'timeline' AND entity_id = OLD.id"
            "    AND title = OLD.title"
            "    AND body = COALESCE(OLD.description, '') || ' ' || COALESCE(OLD.note, '');"
            " END"
        )
    )

    # -- graph_nodes -------------------------------------------------------
    _drop_triggers(conn, "graph_nodes")
    conn.execute(
        text(
            "CREATE TRIGGER graph_nodes_fts_ai AFTER INSERT ON graph_nodes"
            " WHEN NEW.deleted_at IS NULL BEGIN"
            f"  INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  VALUES(NEW.project_id, 'graph', NEW.id,"
            "    NEW.title, COALESCE(NEW.summary, ''),"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0'));"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER graph_nodes_fts_au AFTER UPDATE ON graph_nodes BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'graph' AND entity_id = OLD.id"
            "    AND title = OLD.title"
            "    AND body = COALESCE(OLD.summary, '');"
            "  INSERT INTO"
            f"    {FTS_TABLE}(project_id, entity_type, entity_id,"
            "    title, body, tags, metadata_json, updated_at)"
            "  SELECT NEW.project_id, 'graph', NEW.id,"
            "    NEW.title, COALESCE(NEW.summary, ''),"
            "    '', '{}',"
            "    COALESCE(strftime('%s', NEW.updated_at), '0')"
            "  WHERE NEW.deleted_at IS NULL;"
            " END"
        )
    )
    conn.execute(
        text(
            "CREATE TRIGGER graph_nodes_fts_ad AFTER DELETE ON graph_nodes BEGIN"
            f"  DELETE FROM {FTS_TABLE} WHERE"
            "    entity_type = 'graph' AND entity_id = OLD.id"
            "    AND title = OLD.title"
            "    AND body = COALESCE(OLD.summary, '');"
            " END"
        )
    )


def _drop_triggers(conn: Connection, table: str) -> None:
    """Drop all FTS triggers for a given source table."""
    for suffix in ("ai", "au", "ad"):
        conn.execute(text(f"DROP TRIGGER IF EXISTS {table}_fts_{suffix}"))


# ---------------------------------------------------------------------------
# Backfill
# ---------------------------------------------------------------------------


def _backfill_fts_index(conn: Connection, tokenizer: str) -> None:  # noqa: ARG001
    """Rebuild the entire FTS index from source tables."""
    # Clear existing index
    conn.execute(
        text(f"DELETE FROM {FTS_TABLE} WHERE project_id IS NOT NULL")
    )

    # chapters
    conn.execute(
        text(
            f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "  title, body, tags, metadata_json, updated_at)"
            " SELECT project_id, 'chapter', id,"
            "  title, COALESCE(content, ''),"
            "  '', '{}',"
            "  COALESCE(strftime('%s', updated_at), '0')"
            " FROM chapters WHERE deleted_at IS NULL"
        )
    )

    # setting_items
    conn.execute(
        text(
            f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "  title, body, tags, metadata_json, updated_at)"
            " SELECT project_id, 'setting', id,"
            "  title,"
            "  CASE WHEN node_kind = 'folder' THEN ''"
            "    ELSE COALESCE(summary, '') || ' ' || COALESCE(detail, '') END,"
            "  COALESCE(tags, ''), '{}',"
            "  COALESCE(strftime('%s', updated_at), '0')"
            " FROM setting_items WHERE deleted_at IS NULL"
        )
    )

    # characters
    conn.execute(
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
            " FROM characters WHERE deleted_at IS NULL"
        )
    )

    # clues
    conn.execute(
        text(
            f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "  title, body, tags, metadata_json, updated_at)"
            " SELECT project_id, 'clue', id,"
            "  title,"
            "  COALESCE(description, '') || ' ' || COALESCE(note, '')"
            "  || ' ' || COALESCE(payoff_plan, '') || ' ' || COALESCE(actual_payoff, ''),"
            "  '', '{}',"
            "  COALESCE(strftime('%s', updated_at), '0')"
            " FROM clues WHERE deleted_at IS NULL"
        )
    )

    # outline_items
    conn.execute(
        text(
            f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "  title, body, tags, metadata_json, updated_at)"
            " SELECT project_id, 'outline', id,"
            "  title, COALESCE(content, ''),"
            "  '', '{}',"
            "  COALESCE(strftime('%s', updated_at), '0')"
            " FROM outline_items WHERE deleted_at IS NULL"
        )
    )

    # knowledge_chunks
    conn.execute(
        text(
            f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "  title, body, tags, metadata_json, updated_at)"
            " SELECT project_id, 'knowledge', id,"
            "  COALESCE(heading, ''), COALESCE(content, ''),"
            "  '', json_object('source_id', source_id),"
            "  COALESCE(strftime('%s', updated_at), '0')"
            " FROM knowledge_chunks WHERE deleted_at IS NULL"
        )
    )

    # timeline_events
    conn.execute(
        text(
            f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "  title, body, tags, metadata_json, updated_at)"
            " SELECT project_id, 'timeline', id,"
            "  title,"
            "  COALESCE(description, '') || ' ' || COALESCE(note, ''),"
            "  '', '{}',"
            "  COALESCE(strftime('%s', updated_at), '0')"
            " FROM timeline_events WHERE deleted_at IS NULL"
        )
    )

    # graph_nodes
    conn.execute(
        text(
            f"INSERT INTO {FTS_TABLE}(project_id, entity_type, entity_id,"
            "  title, body, tags, metadata_json, updated_at)"
            " SELECT project_id, 'graph', id,"
            "  title, COALESCE(summary, ''),"
            "  '', '{}',"
            "  COALESCE(strftime('%s', updated_at), '0')"
            " FROM graph_nodes WHERE deleted_at IS NULL"
        )
    )
