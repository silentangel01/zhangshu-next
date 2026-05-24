from collections.abc import Generator
import os
from pathlib import Path

from uuid import uuid4

from sqlalchemy import create_engine, inspect, select, text, update
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATABASE_DIR = Path(os.environ.get("ZHANGSHU_DATA_DIR", BACKEND_DIR.parent / "data")).resolve()
DATABASE_PATH = DATABASE_DIR / os.environ.get("ZHANGSHU_DB_FILENAME", "zhangshu_dev.sqlite3")
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


class Base(DeclarativeBase):
    pass


def ensure_database_directory() -> None:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)


ensure_database_directory()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _ensure_timeline_event_columns() -> bool:
    inspector = inspect(engine)
    if "timeline_events" not in inspector.get_table_names():
        return False

    existing_columns = {column["name"] for column in inspector.get_columns("timeline_events")}
    added_position_ratio = False
    with engine.begin() as connection:
        if "track_id" not in existing_columns:
            connection.execute(text("ALTER TABLE timeline_events ADD COLUMN track_id VARCHAR(36)"))
        if "position_index" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE timeline_events ADD COLUMN position_index INTEGER NOT NULL DEFAULT 0"
                )
            )
        if "position_ratio" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE timeline_events ADD COLUMN position_ratio FLOAT NOT NULL DEFAULT 50.0"
                )
            )
            added_position_ratio = True

    return added_position_ratio


def _ensure_timeline_edge_columns() -> bool:
    inspector = inspect(engine)
    if "timeline_edges" not in inspector.get_table_names():
        return False

    existing_columns = {column["name"] for column in inspector.get_columns("timeline_edges")}
    added_temporal_relation = False
    with engine.begin() as connection:
        if "temporal_relation" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE timeline_edges ADD COLUMN temporal_relation VARCHAR(32) NOT NULL DEFAULT 'unordered'"
                )
            )
            added_temporal_relation = True

        missing_temporal_relation_count = connection.scalar(
            text(
                "SELECT COUNT(*) FROM timeline_edges WHERE temporal_relation IS NULL OR temporal_relation=''"
            )
        )
        if missing_temporal_relation_count:
            connection.execute(
                text(
                    "UPDATE timeline_edges SET temporal_relation='unordered' WHERE temporal_relation IS NULL OR temporal_relation=''"
                )
            )

    return added_temporal_relation


def _ensure_graph_node_size_columns() -> None:
    inspector = inspect(engine)
    if "graph_nodes" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("graph_nodes")}
    with engine.begin() as connection:
        added_width = "width" not in existing_columns
        added_height = "height" not in existing_columns
        if "width" not in existing_columns:
            connection.execute(
                text("ALTER TABLE graph_nodes ADD COLUMN width FLOAT NOT NULL DEFAULT 160")
            )
        if "height" not in existing_columns:
            connection.execute(
                text("ALTER TABLE graph_nodes ADD COLUMN height FLOAT NOT NULL DEFAULT 72")
            )
        width_where = "1 = 1" if added_width else "width IS NULL OR width <= 0"
        height_where = "1 = 1" if added_height else "height IS NULL OR height <= 0"
        width_count = connection.scalar(text(f"SELECT COUNT(*) FROM graph_nodes WHERE {width_where}"))
        if width_count:
            connection.execute(
                text(
                    f"""
                    UPDATE graph_nodes
                    SET width = CASE
                        WHEN size = 1 THEN 120
                        WHEN size = 2 THEN 160
                        WHEN size = 3 THEN 220
                        ELSE 160
                    END
                    WHERE {width_where}
                    """
                )
            )
        height_count = connection.scalar(text(f"SELECT COUNT(*) FROM graph_nodes WHERE {height_where}"))
        if height_count:
            connection.execute(
                text(
                    f"""
                    UPDATE graph_nodes
                    SET height = CASE
                        WHEN size = 1 THEN 56
                        WHEN size = 2 THEN 72
                        WHEN size = 3 THEN 96
                        ELSE 72
                    END
                    WHERE {height_where}
                    """
                )
            )


def _backfill_timeline_tracks() -> None:
    from app.models.timeline_event import TimelineEvent
    from app.models.timeline_track import TimelineTrack

    db = SessionLocal()
    try:
        project_ids = [
            row[0]
            for row in db.execute(
                select(TimelineEvent.project_id)
                .where(TimelineEvent.deleted_at.is_(None))
                .distinct()
            ).all()
        ]

        for project_id in project_ids:
            main_track = db.scalar(
                select(TimelineTrack).where(
                    TimelineTrack.project_id == project_id,
                    TimelineTrack.deleted_at.is_(None),
                    TimelineTrack.is_main.is_(True),
                )
            )

            if main_track is None:
                main_track = TimelineTrack(
                    id=str(uuid4()),
                    project_id=project_id,
                    title="全书主时间轴",
                    track_type="main",
                    is_main=True,
                    order_index=0,
                )
                db.add(main_track)
                db.flush()

            db.execute(
                update(TimelineEvent)
                .where(
                    TimelineEvent.project_id == project_id,
                    TimelineEvent.deleted_at.is_(None),
                    TimelineEvent.track_id.is_(None),
                )
                .values(track_id=main_track.id, position_index=TimelineEvent.order_index)
            )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _backfill_timeline_event_position_ratios() -> None:
    from app.models.timeline_event import TimelineEvent
    from app.models.timeline_track import TimelineTrack

    db = SessionLocal()
    try:
        project_ids = [
            row[0]
            for row in db.execute(
                select(TimelineEvent.project_id)
                .where(TimelineEvent.deleted_at.is_(None))
                .distinct()
            ).all()
        ]

        for project_id in project_ids:
            tracks = list(
                db.scalars(
                    select(TimelineTrack)
                    .where(
                        TimelineTrack.project_id == project_id,
                        TimelineTrack.deleted_at.is_(None),
                    )
                    .order_by(
                        TimelineTrack.is_main.desc(),
                        TimelineTrack.order_index.asc(),
                        TimelineTrack.created_at.asc(),
                    )
                ).all()
            )

            for track in tracks:
                events = list(
                    db.scalars(
                        select(TimelineEvent)
                        .where(
                            TimelineEvent.project_id == project_id,
                            TimelineEvent.deleted_at.is_(None),
                            TimelineEvent.track_id == track.id,
                        )
                        .order_by(
                            TimelineEvent.position_index.asc(),
                            TimelineEvent.order_index.asc(),
                            TimelineEvent.created_at.asc(),
                        )
                    ).all()
                )
                event_count = len(events)
                if event_count == 0:
                    continue

                for index, event in enumerate(events):
                    if event_count == 1:
                        event.position_ratio = 50.0
                    else:
                        event.position_ratio = round(100.0 * (index + 1) / (event_count + 1), 2)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _ensure_setting_tree_columns() -> None:
    inspector = inspect(engine)
    if "setting_items" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("setting_items")}
    with engine.begin() as connection:
        if "node_kind" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE setting_items ADD COLUMN node_kind VARCHAR(16) NOT NULL DEFAULT 'page'"
                )
            )
        if "folder_key" not in existing_columns:
            connection.execute(
                text("ALTER TABLE setting_items ADD COLUMN folder_key VARCHAR(64)")
            )
        if "folder_default_item_type" not in existing_columns:
            connection.execute(
                text("ALTER TABLE setting_items ADD COLUMN folder_default_item_type VARCHAR(32)")
            )
        if "is_system" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE setting_items ADD COLUMN is_system BOOLEAN NOT NULL DEFAULT 0"
                )
            )


def _ensure_project_book_columns() -> None:
    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("projects")}
    with engine.begin() as connection:
        if "author" not in existing_columns:
            connection.execute(
                text("ALTER TABLE projects ADD COLUMN author VARCHAR(128)")
            )
        if "tags" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE projects ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'"
                )
            )
        if "cover_image_path" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE projects ADD COLUMN cover_image_path VARCHAR(500)"
                )
            )
        if "status" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE projects ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'planning'"
                )
            )
        if "target_word_count" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE projects ADD COLUMN target_word_count INTEGER"
                )
            )


def _ensure_knowledge_index_profile_columns() -> None:
    inspector = inspect(engine)
    if "knowledge_index_profiles" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("knowledge_index_profiles")
    }
    with engine.begin() as connection:
        if "provider_type" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE knowledge_index_profiles "
                    "ADD COLUMN provider_type VARCHAR(32) NOT NULL DEFAULT 'compat'"
                )
            )
        if "display_name" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE knowledge_index_profiles "
                    "ADD COLUMN display_name VARCHAR(128) NOT NULL DEFAULT ''"
                )
            )
        if "chunk_size" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE knowledge_index_profiles "
                    "ADD COLUMN chunk_size VARCHAR(16) NOT NULL DEFAULT 'medium'"
                )
            )
        if "status" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE knowledge_index_profiles "
                    "ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'ready'"
                )
            )
        if "last_refreshed_at" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE knowledge_index_profiles "
                    "ADD COLUMN last_refreshed_at DATETIME"
                )
            )
        if "last_error" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE knowledge_index_profiles ADD COLUMN last_error TEXT"
                )
            )


def init_database() -> None:
    from app.models import project  # noqa: F401
    from app.models import volume  # noqa: F401
    from app.models import chapter  # noqa: F401
    from app.models import chapter_character  # noqa: F401
    from app.models import chapter_clue  # noqa: F401
    from app.models import chapter_setting  # noqa: F401
    from app.models import chapter_version  # noqa: F401
    from app.models import check_result  # noqa: F401
    from app.models import character  # noqa: F401
    from app.models import clue  # noqa: F401
    from app.models import clue_character  # noqa: F401
    from app.models import clue_setting  # noqa: F401
    from app.models import graph_edge  # noqa: F401
    from app.models import graph_node  # noqa: F401
    from app.models import outline_item  # noqa: F401
    from app.models import outline_item_character  # noqa: F401
    from app.models import outline_item_clue  # noqa: F401
    from app.models import outline_item_setting  # noqa: F401
    from app.models import outline_item_timeline_event  # noqa: F401
    from app.models import prohibited_term  # noqa: F401
    from app.models import recovery_draft  # noqa: F401
    from app.models import timeline_event  # noqa: F401
    from app.models import timeline_event_character  # noqa: F401
    from app.models import timeline_event_clue  # noqa: F401
    from app.models import timeline_event_setting  # noqa: F401
    from app.models import timeline_edge  # noqa: F401
    from app.models import timeline_track  # noqa: F401
    from app.models import setting_item  # noqa: F401
    from app.models import knowledge_source  # noqa: F401
    from app.models import knowledge_chunk  # noqa: F401
    from app.models import knowledge_link  # noqa: F401
    from app.models import knowledge_embedding  # noqa: F401
    from app.models import knowledge_index_profile  # noqa: F401
    from app.models import app_config  # noqa: F401

    ensure_database_directory()
    Base.metadata.create_all(bind=engine)
    _ensure_project_book_columns()
    _ensure_setting_tree_columns()
    _ensure_graph_node_size_columns()
    added_position_ratio = _ensure_timeline_event_columns()
    _ensure_timeline_edge_columns()
    _ensure_knowledge_index_profile_columns()
    _backfill_timeline_tracks()
    if added_position_ratio:
        _backfill_timeline_event_position_ratios()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
