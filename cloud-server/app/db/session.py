"""Database engine and session factory.

Engine configuration is tailored to the database type:

- **SQLite** (development/tests): single-thread, no pool configuration,
  ``check_same_thread=False`` to allow sharing across threads.
- **PostgreSQL** (production): explicit pool size, overflow, timeout,
  recycle, connect timeout, and statement timeout from settings.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def _build_engine_kwargs() -> dict:
    """Build keyword arguments for :func:`create_engine`.

    SQLite and PostgreSQL require different sets of arguments. PostgreSQL
    specific options (pool tuning, statement timeout) must not be passed
    when using SQLite — SQLAlchemy would raise or silently ignore them.
    """
    url = settings.database_url

    if url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "pool_pre_ping": True,
        }

    # PostgreSQL (or any other supported dialect)
    connect_args: dict = {
        "connect_timeout": settings.database_connect_timeout_seconds,
    }
    if settings.database_statement_timeout_ms > 0:
        connect_args["options"] = (
            f"-c statement_timeout={settings.database_statement_timeout_ms}"
        )

    return {
        "connect_args": connect_args,
        "pool_pre_ping": True,
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout_seconds,
        "pool_recycle": settings.database_pool_recycle_seconds,
    }


engine = create_engine(settings.database_url, **_build_engine_kwargs())

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
