"""sqlite-vec vector index for image embeddings (ADR-001, ADR-022, ADR-024).

Two independent `vec0` virtual tables live in the main DB, both keyed by
`asset.id` as rowid:

- `vec_asset_embedding` — SigLIP2 semantic-search space (`float[1024]`), canonical
  BLOB on `asset.clip_embedding`.
- `vec_asset_dino` — DINOv2 visual-rerank space (`float[768]`, P37/ADR-024),
  canonical BLOB on `asset.dino_embedding`.

The two spaces are separate on purpose: different models, different dimensions,
no shared index. An asset may sit in one, both, or neither — a missing DINOv2
row is a valid state (rerank degrades to plain SigLIP2, P37 Phase 3).

Each table is a rebuildable index over its canonical BLOB column, so any drift
between the two is forward-recoverable (`rebuild_index`). The shared SQL/serialize
logic is written once and parametrized by table + dim; the public functions below
pin those parameters per space so callers name a space, not a table.

The sqlite-vec extension is loaded per connection: at runtime via the SQLAlchemy
`connect` event (`photofant/db/engine.py`), and inside the migrations that create
the tables (on `op.get_bind()`).
"""
from __future__ import annotations

import contextlib
import logging
import sqlite3

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# Dimension of a vec0 table = schema truth for that space; the active embedder for
# the matching role must match it (startup dim-guard).
# SigLIP2-large-patch16-384 → shared 1024-dim image/text space (role semantic_search).
EMBEDDING_DIM: int = 1024
_TABLE = "vec_asset_embedding"

# DINOv2-with-registers-base → 768-dim visual-only space (role visual_rerank, P37).
DINO_EMBEDDING_DIM: int = 768
_DINO_TABLE = "vec_asset_dino"


def _create_table_sql(table: str, dim: int) -> str:
    return (
        f"CREATE VIRTUAL TABLE IF NOT EXISTS {table} "
        f"USING vec0(embedding float[{dim}] distance_metric=cosine)"
    )


# SigLIP2 index DDL — kept as a module constant because migration 0007 imports it.
CREATE_TABLE_SQL = _create_table_sql(_TABLE, EMBEDDING_DIM)
# DINOv2 index DDL — imported by the P37 migration that creates vec_asset_dino.
DINO_CREATE_TABLE_SQL = _create_table_sql(_DINO_TABLE, DINO_EMBEDDING_DIM)


def load_vec_extension(dbapi_connection: sqlite3.Connection) -> None:
    """Load the sqlite-vec loadable extension onto a raw DBAPI connection.

    Idempotent per connection; safe to call from the engine connect-event and
    from a migration. Raises RuntimeError if the extension cannot be loaded so a
    half-configured connection never gets used for a vector query.
    """
    import sqlite_vec

    try:
        dbapi_connection.enable_load_extension(True)
        sqlite_vec.load(dbapi_connection)
    except (AttributeError, sqlite3.OperationalError) as error:
        raise RuntimeError(f"Could not load sqlite-vec extension: {error}") from error
    finally:
        # Re-disable extension loading — we only need it during setup.
        with contextlib.suppress(AttributeError, sqlite3.OperationalError):
            dbapi_connection.enable_load_extension(False)


# ----------------------------------------------------------------------------
# Parametrized core — one implementation, pinned per space by the public API
# ----------------------------------------------------------------------------


def _serialize(embedding: np.ndarray, dim: int) -> bytes:
    """Pack a 1-D embedding into the float32 byte layout sqlite-vec expects."""
    vector = np.ascontiguousarray(embedding, dtype=np.float32).reshape(-1)
    if vector.shape[0] != dim:
        raise ValueError(f"Embedding has dim {vector.shape[0]}, expected {dim}")
    return vector.tobytes()


def _index_available(session: Session, table: str) -> bool:
    """True if *table* exists on this connection.

    The index is a rebuildable secondary structure created only by a migration
    (it is not part of `Base.metadata`). Connections without the extension/table
    — e.g. throw-away test DBs — degrade gracefully instead of crashing.
    """
    row = session.execute(
        text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"),
        {"name": table},
    ).first()
    return row is not None


def _upsert(session: Session, table: str, dim: int, asset_id: int, embedding: np.ndarray) -> None:
    """Insert or replace the *table* row for *asset_id* (no commit — caller owns the tx)."""
    blob = _serialize(embedding, dim)
    if not _index_available(session, table):
        log.warning("Vector index %s missing — skipping upsert for asset %d", table, asset_id)
        return
    session.execute(text(f"DELETE FROM {table} WHERE rowid = :rowid"), {"rowid": asset_id})
    session.execute(
        text(f"INSERT INTO {table}(rowid, embedding) VALUES (:rowid, :embedding)"),
        {"rowid": asset_id, "embedding": blob},
    )


def _delete(session: Session, table: str, asset_id: int) -> None:
    """Remove the *table* row for *asset_id* if present (no commit)."""
    if not _index_available(session, table):
        return
    session.execute(text(f"DELETE FROM {table} WHERE rowid = :rowid"), {"rowid": asset_id})


def _search(
    session: Session, table: str, dim: int, query_embedding: np.ndarray, limit: int
) -> list[tuple[int, float]]:
    """Return up to *limit* (asset_id, cosine_similarity) pairs from *table*, most similar first."""
    blob = _serialize(query_embedding, dim)
    if not _index_available(session, table):
        return []
    rows = session.execute(
        text(
            f"SELECT rowid, distance FROM {table} "
            f"WHERE embedding MATCH :query ORDER BY distance LIMIT :limit"
        ),
        {"query": blob, "limit": limit},
    ).fetchall()
    return [(int(asset_id), 1.0 - float(distance)) for asset_id, distance in rows]


def _rebuild(session: Session, table: str, source_column: str) -> int:
    """Rebuild *table* from the `asset.<source_column>` BLOBs. Returns row count.

    Used to heal index/BLOB drift or to populate the index for an existing
    library. Commits its own transaction.
    """
    if not _index_available(session, table):
        log.warning("Vector index %s missing — cannot rebuild", table)
        return 0

    session.execute(text(f"DELETE FROM {table}"))
    rows = session.execute(
        text(f"SELECT id, {source_column} FROM asset WHERE {source_column} IS NOT NULL")
    ).fetchall()

    inserted = 0
    for asset_id, blob in rows:
        if blob is None:
            continue
        session.execute(
            text(f"INSERT INTO {table}(rowid, embedding) VALUES (:rowid, :embedding)"),
            {"rowid": int(asset_id), "embedding": bytes(blob)},
        )
        inserted += 1

    session.commit()
    log.info("Rebuilt vector index %s: %d embedding(s)", table, inserted)
    return inserted


# ----------------------------------------------------------------------------
# SigLIP2 semantic-search space (vec_asset_embedding) — stable public API
# ----------------------------------------------------------------------------


def upsert_embedding(session: Session, asset_id: int, embedding: np.ndarray) -> None:
    """Insert or replace the SigLIP2 index row for *asset_id* (no commit)."""
    _upsert(session, _TABLE, EMBEDDING_DIM, asset_id, embedding)


def delete_embedding(session: Session, asset_id: int) -> None:
    """Remove the SigLIP2 index row for *asset_id* if present (no commit)."""
    _delete(session, _TABLE, asset_id)


def search(session: Session, query_embedding: np.ndarray, limit: int) -> list[tuple[int, float]]:
    """Return up to *limit* (asset_id, cosine_similarity) pairs from the SigLIP2 space."""
    return _search(session, _TABLE, EMBEDDING_DIM, query_embedding, limit)


def rebuild_index(session: Session) -> int:
    """Rebuild the SigLIP2 index from `asset.clip_embedding` BLOBs. Returns row count."""
    return _rebuild(session, _TABLE, "clip_embedding")


# ----------------------------------------------------------------------------
# DINOv2 visual-rerank space (vec_asset_dino) — P37
# ----------------------------------------------------------------------------


def upsert_dino_embedding(session: Session, asset_id: int, embedding: np.ndarray) -> None:
    """Insert or replace the DINOv2 index row for *asset_id* (no commit)."""
    _upsert(session, _DINO_TABLE, DINO_EMBEDDING_DIM, asset_id, embedding)


def delete_dino_embedding(session: Session, asset_id: int) -> None:
    """Remove the DINOv2 index row for *asset_id* if present (no commit)."""
    _delete(session, _DINO_TABLE, asset_id)
