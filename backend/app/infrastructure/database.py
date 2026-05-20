from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
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


def init_database() -> None:
    from app.models import project  # noqa: F401
    from app.models import volume  # noqa: F401
    from app.models import chapter  # noqa: F401
    from app.models import chapter_character  # noqa: F401
    from app.models import chapter_version  # noqa: F401
    from app.models import character  # noqa: F401
    from app.models import outline_item  # noqa: F401

    ensure_database_directory()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
