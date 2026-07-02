from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from photofant.config import get_data_root_base
from photofant.settings import load_settings


def _resolve_db_path() -> Path:
    raw = load_settings()["db_path"]
    path = Path(raw) if raw else get_data_root_base() / ".photofant" / "db.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    return _resolve_db_path()


def create_db_engine() -> Engine:
    db_path = _resolve_db_path()
    url = f"sqlite:///{db_path}"
    new_engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30},
        # QueuePool (SQLAlchemy default when poolclass is omitted) instead of NullPool:
        # physical connections are reused across requests, so the WAL pragma + sqlite-vec
        # extension load in the connect-event below fire once per pooled connection
        # instead of once per request.
        pool_size=5,
        max_overflow=10,
    )

    @event.listens_for(new_engine, "connect")
    def _configure_connection(dbapi_connection: sqlite3.Connection, _record: Any) -> None:
        # WAL mode: concurrent readers + one writer, no "database is locked" on parallel jobs.
        # synchronous=NORMAL is safe with WAL and avoids unnecessary fsync overhead.
        dbapi_connection.execute("PRAGMA journal_mode=WAL")
        dbapi_connection.execute("PRAGMA synchronous=NORMAL")
        # Every connection needs the sqlite-vec extension so vec0 queries work (ADR-001).
        from photofant.db.vector_index import load_vec_extension

        load_vec_extension(dbapi_connection)

    return new_engine


engine = create_db_engine()
