from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_CACHE_DB_PATH = Path(".photofant") / "thumbnails.sqlite"

THUMBNAIL_SIZES: tuple[int, ...] = (256, 512)


def get_cache_db_path() -> Path:
    raw = os.environ.get("PHOTOFANT_CACHE_DB_PATH", str(_DEFAULT_CACHE_DB_PATH))
    path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_cache_db(db_path: Path) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS thumbnail (
                target_kind TEXT NOT NULL,
                target_id   INTEGER NOT NULL,
                size        INTEGER NOT NULL,
                blob        BLOB NOT NULL,
                PRIMARY KEY (target_kind, target_id, size)
            )
        """)
        con.commit()
    finally:
        con.close()


def get_thumbnail(db_path: Path, target_id: int, size: int, target_kind: str = "asset") -> bytes | None:
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT blob FROM thumbnail WHERE target_kind = ? AND target_id = ? AND size = ?",
            (target_kind, target_id, size),
        ).fetchone()
        return bytes(row[0]) if row else None
    finally:
        con.close()


def store_thumbnail(db_path: Path, target_id: int, size: int, data: bytes, target_kind: str = "asset") -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "INSERT OR REPLACE INTO thumbnail (target_kind, target_id, size, blob) VALUES (?, ?, ?, ?)",
            (target_kind, target_id, size, data),
        )
        con.commit()
    finally:
        con.close()


def clear_cache(db_path: Path) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute("DELETE FROM thumbnail")
        con.commit()
    finally:
        con.close()
