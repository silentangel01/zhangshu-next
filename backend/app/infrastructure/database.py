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


def _ensure_timeline_event_columns() -> None:
    inspector = inspect(engine)
    if "timeline_events" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("timeline_events")}
    with engine.begin() as connection:
        if "track_id" not in existing_columns:
            connection.execute(text("ALTER TABLE timeline_events ADD COLUMN track_id VARCHAR(36)"))
        if "position_index" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE timeline_events ADD COLUMN position_index INTEGER NOT NULL DEFAULT 0"
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
    from app.models import outline_item  # noqa: F401
    from app.models import timeline_event  # noqa: F401
    from app.models import timeline_edge  # noqa: F401
    from app.models import timeline_track  # noqa: F401
    from app.models import setting_item  # noqa: F401

    ensure_database_directory()
    Base.metadata.create_all(bind=engine)
    _ensure_timeline_event_columns()
    _backfill_timeline_tracks()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
