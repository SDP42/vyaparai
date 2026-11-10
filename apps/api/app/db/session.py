"""Engine and session factory."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def build_engine(database_url: str, *, echo: bool = False, **kwargs: Any) -> Engine:
    if database_url.startswith("sqlite"):
        kwargs.setdefault("connect_args", {"check_same_thread": False})
    elif database_url.startswith("postgres"):
        s = get_settings()
        kwargs.setdefault("pool_size", s.db_pool_size)
        kwargs.setdefault("max_overflow", s.db_max_overflow)
        kwargs.setdefault("pool_recycle", 1800)
    engine = create_engine(database_url, echo=echo, pool_pre_ping=True, **kwargs)
    if engine.dialect.name == "sqlite":
        _enable_sqlite_foreign_keys(engine)
    elif engine.dialect.name == "postgresql":
        _set_statement_timeout(engine, get_settings().db_statement_timeout_ms)
    return engine


def _set_statement_timeout(engine: Engine, ms: int) -> None:
    """A slow query is stopped by PostgreSQL itself: the application cannot interrupt a running statement."""

    @event.listens_for(engine, "connect")
    def _timeout(dbapi_conn: Any, _: Any) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET statement_timeout = {int(ms)}")
        cursor.close()


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn: Any, _: Any) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return build_engine(settings.database_url, echo=settings.database_echo)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    with get_session_factory()() as session:
        yield session
