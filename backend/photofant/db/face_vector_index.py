"""sqlite-vec vector index for ArcFace embeddings (face clustering / matching).

Same pattern as vector_index.py (CLIP), but for the 512-dim ArcFace face
embeddings stored in ``face.embedding``. The searchable index is a ``vec0``
virtual table (``vec_face_embedding``) living in the main DB; its rowid is
``face.id``.
"""
from __future__ import annotations

import contextlib
import logging
import sqlite3

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

FACE_EMBEDDING_DIM: int = 512
_TABLE = "vec_face_embedding"

CREATE_TABLE_SQL = (
    f"CREATE VIRTUAL TABLE IF NOT EXISTS {_TABLE} "
    f"USING vec0(embedding float[{FACE_EMBEDDING_DIM}] distance_metric=cosine)"
)


def load_vec_extension(dbapi_connection: sqlite3.Connection) -> None:
    import sqlite_vec

    try:
        dbapi_connection.enable_load_extension(True)
        sqlite_vec.load(dbapi_connection)
    except (AttributeError, sqlite3.OperationalError) as error:
        raise RuntimeError(f"Could not load sqlite-vec extension: {error}") from error
    finally:
        with contextlib.suppress(AttributeError, sqlite3.OperationalError):
            dbapi_connection.enable_load_extension(False)


def _serialize(embedding: np.ndarray) -> bytes:
    vector = np.ascontiguousarray(embedding, dtype=np.float32).reshape(-1)
    if vector.shape[0] != FACE_EMBEDDING_DIM:
        raise ValueError(f"Face embedding has dim {vector.shape[0]}, expected {FACE_EMBEDDING_DIM}")
    return vector.tobytes()


def deserialize(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32).copy()


def _index_available(session: Session) -> bool:
    row = session.execute(
        text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"),
        {"name": _TABLE},
    ).first()
    return row is not None


def upsert_embedding(session: Session, face_id: int, embedding: np.ndarray) -> None:
    blob = _serialize(embedding)
    if not _index_available(session):
        log.warning("Face vector index missing — skipping upsert for face %d", face_id)
        return
    session.execute(text(f"DELETE FROM {_TABLE} WHERE rowid = :rowid"), {"rowid": face_id})
    session.execute(
        text(f"INSERT INTO {_TABLE}(rowid, embedding) VALUES (:rowid, :embedding)"),
        {"rowid": face_id, "embedding": blob},
    )


def delete_embedding(session: Session, face_id: int) -> None:
    if not _index_available(session):
        return
    session.execute(text(f"DELETE FROM {_TABLE} WHERE rowid = :rowid"), {"rowid": face_id})


def search(session: Session, query_embedding: np.ndarray, limit: int) -> list[tuple[int, float]]:
    """Return up to *limit* (face_id, cosine_similarity) pairs, most similar first."""
    blob = _serialize(query_embedding)
    if not _index_available(session):
        return []
    rows = session.execute(
        text(
            f"SELECT rowid, distance FROM {_TABLE} "
            f"WHERE embedding MATCH :query ORDER BY distance LIMIT :limit"
        ),
        {"query": blob, "limit": limit},
    ).fetchall()
    return [(int(face_id), 1.0 - float(distance)) for face_id, distance in rows]


def search_disjoint_persons(
    session: Session,
    query_embedding: np.ndarray,
    exclude_face_id: int | None = None,
    limit: int = 10,
) -> list[dict[str, int | float]]:
    """Top *limit* disjoint persons — best face per person, sorted by score descending.

    Returns dicts with keys: person_id, best_face_id, score.
    """
    from photofant.db.models import Face

    raw_hits = search(session, query_embedding, limit=limit * 5)

    if exclude_face_id is not None:
        raw_hits = [(fid, score) for fid, score in raw_hits if fid != exclude_face_id]

    face_ids = [fid for fid, _ in raw_hits]
    if not face_ids:
        return []

    faces = session.query(Face.id, Face.person_id).filter(Face.id.in_(face_ids)).all()
    person_map: dict[int, int] = {row.id: row.person_id for row in faces if row.person_id is not None}

    seen_persons: set[int] = set()
    results: list[dict[str, int | float]] = []
    for face_id, score in raw_hits:
        person_id = person_map.get(face_id)
        if person_id is None or person_id in seen_persons:
            continue
        seen_persons.add(person_id)
        results.append({"person_id": person_id, "best_face_id": face_id, "score": score})
        if len(results) >= limit:
            break

    return results


def rebuild_index(session: Session) -> int:
    """Rebuild the face vector index from all ``face.embedding`` BLOBs."""
    if not _index_available(session):
        log.warning("Face vector index table missing — cannot rebuild")
        return 0

    session.execute(text(f"DELETE FROM {_TABLE}"))
    rows = session.execute(
        text("SELECT id, embedding FROM face WHERE embedding IS NOT NULL")
    ).fetchall()

    inserted = 0
    for face_id, blob in rows:
        if blob is None:
            continue
        session.execute(
            text(f"INSERT INTO {_TABLE}(rowid, embedding) VALUES (:rowid, :embedding)"),
            {"rowid": int(face_id), "embedding": bytes(blob)},
        )
        inserted += 1

    session.commit()
    log.info("Rebuilt face vector index: %d embedding(s)", inserted)
    return inserted
