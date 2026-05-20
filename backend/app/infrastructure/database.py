from collections.abc import Generator
from pathlib import Path

from uuid import uuid4

from sqlalchemy import create_engine, inspect, select, text, update
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATABASE_DIR = BACKEND_DIR.parent / "data"
DATABASE_PATH = DATABASE_DIR / "zhangshu_dev.sqlite3"
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

        connection.execute(
            text(
                "UPDATE timeline_edges SET temporal_relation='unordered' WHERE temporal_relation IS NULL OR temporal_relation=''"
            )
        )

    return added_temporal_relation


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


def init_database() -> None:
    from app.models import project  # noqa: F401
    from app.models import volume  # noqa: F401
    from app.models import chapter  # noqa: F401
    from app.models import chapter_character  # noqa: F401
    from app.models import chapter_clue  # noqa: F401
    from app.models import chapter_setting  # noqa: F401
    from app.models import chapter_version  # noqa: F401
    from app.models import character  # noqa: F401
    from app.models import clue  # noqa: F401
    from app.models import clue_character  # noqa: F401
    from app.models import clue_setting  # noqa: F401
    from app.models import graph_edge  # noqa: F401
    from app.models import graph_node  # noqa: F401
    from app.models import outline_item  # noqa: F401
    from app.models import timeline_event  # noqa: F401
    from app.models import timeline_edge  # noqa: F401
    from app.models import timeline_track  # noqa: F401
    from app.models import setting_item  # noqa: F401

    ensure_database_directory()
    Base.metadata.create_all(bind=engine)
    added_position_ratio = _ensure_timeline_event_columns()
    _ensure_timeline_edge_columns()
    _backfill_timeline_tracks()
    if added_position_ratio:
        _backfill_timeline_event_position_ratios()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
