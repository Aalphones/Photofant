from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from photofant.config import get_data_root_base
from photofant.settings import load_settings

log = logging.getLogger(__name__)

THUMBNAIL_SIZES: tuple[int, ...] = (256, 512, 1024)


def get_cache_db_path() -> Path:
    raw = load_settings()["cache_db_path"]
    path = Path(raw) if raw else get_data_root_base() / ".photofant" / "thumbnails.sqlite"
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
        con.execute("""
            CREATE TABLE IF NOT EXISTS edit_session (
                session_key TEXT PRIMARY KEY,
                kind        TEXT NOT NULL,
                target_id   INTEGER NOT NULL,
                source_path TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS edit_step (
                session_key TEXT NOT NULL,
                seq         INTEGER NOT NULL,
                op          TEXT NOT NULL,
                params      TEXT NOT NULL,
                preview     BLOB,
                PRIMARY KEY (session_key, seq)
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


def delete_thumbnails(db_path: Path, target_id: int, target_kind: str = "asset") -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "DELETE FROM thumbnail WHERE target_kind = ? AND target_id = ?",
            (target_kind, target_id),
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


def count_thumbnail_targets(db_path: Path, target_kind: str = "asset") -> int:
    """Number of distinct targets (e.g. assets) that have at least one cached thumbnail."""
    if not db_path.exists():
        return 0
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT COUNT(DISTINCT target_id) FROM thumbnail WHERE target_kind = ?",
            (target_kind,),
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        con.close()


# ── Edit-Session CRUD ──────────────────────────────────────────────────────────

def create_edit_session(
    db_path: Path, session_key: str, kind: str, target_id: int, source_path: str, created_at: str
) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "INSERT INTO edit_session (session_key, kind, target_id, source_path, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_key, kind, target_id, source_path, created_at),
        )
        con.commit()
    finally:
        con.close()


def get_edit_session(db_path: Path, session_key: str) -> dict | None:  # type: ignore[type-arg]
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT session_key, kind, target_id, source_path, created_at FROM edit_session WHERE session_key = ?",
            (session_key,),
        ).fetchone()
        if row is None:
            return None
        return {"session_key": row[0], "kind": row[1], "target_id": row[2], "source_path": row[3], "created_at": row[4]}
    finally:
        con.close()


def get_edit_steps(db_path: Path, session_key: str, max_seq: int | None = None) -> list[dict]:  # type: ignore[type-arg]
    """Return step rows (without preview blobs) ordered by seq ascending."""
    con = sqlite3.connect(db_path)
    try:
        if max_seq is None:
            rows = con.execute(
                "SELECT seq, op, params FROM edit_step WHERE session_key = ? ORDER BY seq ASC",
                (session_key,),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT seq, op, params FROM edit_step WHERE session_key = ? AND seq <= ? ORDER BY seq ASC",
                (session_key, max_seq),
            ).fetchall()
        return [{"seq": r[0], "op": r[1], "params": r[2], "params_dict": json.loads(r[2])} for r in rows]
    finally:
        con.close()


def append_edit_step(db_path: Path, session_key: str, seq: int, op: str, params_json: str, preview: bytes) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "INSERT OR REPLACE INTO edit_step (session_key, seq, op, params, preview) VALUES (?, ?, ?, ?, ?)",
            (session_key, seq, op, params_json, preview),
        )
        con.commit()
    finally:
        con.close()


def get_edit_step_preview(db_path: Path, session_key: str, seq: int) -> bytes | None:
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT preview FROM edit_step WHERE session_key = ? AND seq = ?",
            (session_key, seq),
        ).fetchone()
        return bytes(row[0]) if row and row[0] else None
    finally:
        con.close()


def truncate_steps_after(db_path: Path, session_key: str, keep_seq: int) -> None:
    """Delete all steps with seq > keep_seq for this session (linear undo branching)."""
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "DELETE FROM edit_step WHERE session_key = ? AND seq > ?",
            (session_key, keep_seq),
        )
        con.commit()
    finally:
        con.close()
