from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_DEFAULT_DB_PATH = Path(".photofant") / "db.sqlite"


def _resolve_db_path() -> Path:
    raw = os.environ.get("PHOTOFANT_DB_PATH", str(_DEFAULT_DB_PATH))
    path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def create_db_engine() -> Engine:
    db_path = _resolve_db_path()
    url = f"sqlite:///{db_path}"
    return create_engine(url, connect_args={"check_same_thread": False})


engine = create_db_engine()
