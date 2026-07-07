"""sqlite-vec vector index for image embeddings (ADR-001, ADR-022).

The searchable index is a `vec0` virtual table (`vec_asset_embedding`) living in
the main DB; its rowid is `asset.id`. The canonical embedding is stored on
`asset.clip_embedding` (float32 BLOB) — this table is a rebuildable index over
those BLOBs, so any drift between the two is forward-recoverable via
`rebuild_index`.

The sqlite-vec extension is loaded per connection: at runtime via the SQLAlchemy
`connect` event (`photofant/db/engine.py`), and inside the migration that creates
the table (on `op.get_bind()`).
"""
from __future__ import annotations

import contextlib
import logging
import sqlite3

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# Dimension of the vec0 table = schema truth for the semantic-search index; the
# active semantic_search embedder must match it (startup dim-guard). SigLIP2-large-
# patch16-384 projects image and text to a shared 1024-dim space.
EMBEDDING_DIM: int = 1024
_TABLE = "vec_asset_embedding"

CREATE_TABLE_SQL = (
    f"CREATE VIRTUAL TABLE IF NOT EXISTS {_TABLE} "
    f"USING vec0(embedding float[{EMBEDDING_DIM}] distance_metric=cosine)"
)


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


def _serialize(embedding: np.ndarray) -> bytes:
    """Pack a 1-D embedding into the float32 byte layout sqlite-vec expects."""
    vector = np.ascontiguousarray(embedding, dtype=np.float32).reshape(-1)
    if vector.shape[0] != EMBEDDING_DIM:
        raise ValueError(f"Embedding has dim {vector.shape[0]}, expected {EMBEDDING_DIM}")
    return vector.tobytes()


def _index_available(session: Session) -> bool:
    """True if the vec0 table exists on this connection.

    The index is a rebuildable secondary structure created only by the migration
    (it is not part of `Base.metadata`). Connections without the extension/table
    — e.g. throw-away test DBs — degrade gracefully instead of crashing.
    """
    row = session.execute(
        text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"),
        {"name": _TABLE},
    ).first()
    return row is not None


def upsert_embedding(session: Session, asset_id: int, embedding: np.ndarray) -> None:
    """Insert or replace the index row for *asset_id* (no commit — caller owns the tx)."""
    blob = _serialize(embedding)
    if not _index_available(session):
        log.warning("Vector index missing — skipping upsert for asset %d", asset_id)
        return
    session.execute(text(f"DELETE FROM {_TABLE} WHERE rowid = :rowid"), {"rowid": asset_id})
    session.execute(
        text(f"INSERT INTO {_TABLE}(rowid, embedding) VALUES (:rowid, :embedding)"),
        {"rowid": asset_id, "embedding": blob},
    )


def delete_embedding(session: Session, asset_id: int) -> None:
    """Remove the index row for *asset_id* if present (no commit)."""
    if not _index_available(session):
        return
    session.execute(text(f"DELETE FROM {_TABLE} WHERE rowid = :rowid"), {"rowid": asset_id})


def search(session: Session, query_embedding: np.ndarray, limit: int) -> list[tuple[int, float]]:
    """Return up to *limit* (asset_id, cosine_similarity) pairs, most similar first.

    Cosine similarity = 1 − cosine distance; vec0 returns the distance.
    """
    blob = _serialize(query_embedding)
    rows = session.execute(
        text(
            f"SELECT rowid, distance FROM {_TABLE} "
            f"WHERE embedding MATCH :query ORDER BY distance LIMIT :limit"
        ),
        {"query": blob, "limit": limit},
    ).fetchall()
    return [(int(asset_id), 1.0 - float(distance)) for asset_id, distance in rows]


def rebuild_index(session: Session) -> int:
    """Rebuild the whole index from `asset.clip_embedding` BLOBs. Returns row count.

    Used to heal index/BLOB drift or to populate the index for an existing
    library. Commits its own transaction.
    """
    session.execute(text(f"DELETE FROM {_TABLE}"))
    rows = session.execute(
        text("SELECT id, clip_embedding FROM asset WHERE clip_embedding IS NOT NULL")
    ).fetchall()

    inserted = 0
    for asset_id, blob in rows:
        if blob is None:
            continue
        session.execute(
            text(f"INSERT INTO {_TABLE}(rowid, embedding) VALUES (:rowid, :embedding)"),
            {"rowid": int(asset_id), "embedding": bytes(blob)},
        )
        inserted += 1

    session.commit()
    log.info("Rebuilt vector index: %d embedding(s)", inserted)
    return inserted
