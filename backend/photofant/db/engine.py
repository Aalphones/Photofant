from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from photofant.config import get_data_root_base


def _resolve_db_path() -> Path:
    raw = os.environ.get("PHOTOFANT_DB_PATH")
    path = Path(raw) if raw else get_data_root_base() / ".photofant" / "db.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    return _resolve_db_path()


def create_db_engine() -> Engine:
    db_path = _resolve_db_path()
    url = f"sqlite:///{db_path}"
    new_engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(new_engine, "connect")
    def _load_vec_extension(dbapi_connection: sqlite3.Connection, _record: Any) -> None:
        # Every pooled connection needs the sqlite-vec extension so vec0 queries
        # work through the ORM session (ADR-001).
        from photofant.db.vector_index import load_vec_extension

        load_vec_extension(dbapi_connection)

    return new_engine


engine = create_db_engine()
