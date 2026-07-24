"""Canonical access layer for the two per-asset embedding vectors.

Single seam over the *physical storage* of an asset's embeddings:

- semantic space (SigLIP2, role ``semantic_search``) — source of ``vec_asset_embedding``
- visual space (DINOv2, role ``visual_rerank``, P37) — source of ``vec_asset_dino``

Every module that needs an embedding goes through here; no other module names the
underlying columns. That makes this the *one* place a later move has to touch
(side table, own file, different byte layout — see
``docs/planning/2026-07-21_asset-embeddings-auslagern.md``).

Callers speak in ``numpy`` vectors and asset ids only — never in BLOBs or column
names. Storage today is the ``asset_embedding`` side table (one row per asset,
migration 0043), keyed by ``asset_id``; that is an implementation detail of this
module alone. The old ``asset.clip_embedding`` / ``asset.dino_embedding`` columns
were dropped by migration 0044 (plan phase 3) — the side table is the only copy
left.

This layer owns the *canonical vectors*. The rebuildable ``vec0`` search indexes
over them live in ``photofant/db/vector_index.py`` — a sibling, not a caller of
this module's writers.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from photofant.db.models import Asset, AssetEmbedding

_DTYPE = np.float32


def _to_vector(blob: bytes | None) -> np.ndarray | None:
    """Decode a stored BLOB into a 1-D float32 vector, passing ``None`` through."""
    if blob is None:
        return None
    return np.frombuffer(blob, dtype=_DTYPE)


def _to_blob(embedding: np.ndarray) -> bytes:
    """Encode a vector into the contiguous float32 byte layout used for storage."""
    return np.ascontiguousarray(embedding, dtype=_DTYPE).tobytes()


def _upsert_column(session: Session, asset_id: int, column: str, blob: bytes) -> None:
    """Insert-or-update a single embedding column for *asset_id* (no commit).

    Two embedding jobs for the same asset can legitimately overlap (import plus a
    concurrent repair/reconcile pass) — each runs in its own session, and SQLite
    sessions never see each other's uncommitted work. A get-or-create-then-INSERT
    loses that race: both sessions see "no row yet", both INSERT, and the loser hits
    the ``asset_embedding.asset_id`` UNIQUE constraint (the exact
    ``sqlite3.IntegrityError`` this replaces). ``ON CONFLICT DO UPDATE`` makes the
    write atomic so the race can't produce two competing INSERTs. Still guards
    against a non-existent asset — the SQLite FK is not enforced, so a blind write
    would leave an orphan row.
    """
    if session.get(Asset, asset_id) is None:
        return
    stmt = sqlite_insert(AssetEmbedding).values(asset_id=asset_id, **{column: blob})
    stmt = stmt.on_conflict_do_update(index_elements=[AssetEmbedding.asset_id], set_={column: blob})
    session.execute(stmt)


def delete(session: Session, asset_id: int) -> None:
    """Remove the asset's side row — both vectors go with it (no commit).

    Called from the asset-deletion site: SQLite FK enforcement is off in this app
    (``db/engine.py``), so the side row does not cascade on its own.
    """
    row = session.get(AssetEmbedding, asset_id)
    if row is not None:
        session.delete(row)


# ----------------------------------------------------------------------------
# Semantic space (SigLIP2) — canonical vector behind vec_asset_embedding
# ----------------------------------------------------------------------------


def get_semantic(session: Session, asset_id: int) -> np.ndarray | None:
    """Return the asset's semantic embedding as a float32 vector, or ``None``.

    ``None`` both when the asset does not exist and when it has no embedding yet —
    callers that must tell those apart check asset existence separately.
    """
    blob = session.execute(
        select(AssetEmbedding.clip_embedding).where(AssetEmbedding.asset_id == asset_id)
    ).scalar_one_or_none()
    return _to_vector(blob)


def has_semantic(session: Session, asset_id: int) -> bool:
    """True if the asset has a semantic embedding (cheap existence check)."""
    row = session.execute(
        select(AssetEmbedding.asset_id).where(
            AssetEmbedding.asset_id == asset_id, AssetEmbedding.clip_embedding.is_not(None)
        )
    ).first()
    return row is not None


def assets_with_semantic(session: Session, asset_ids: Sequence[int]) -> set[int]:
    """Subset of *asset_ids* that have a semantic embedding — one batched query.

    Used by list views to resolve the "has embedding" flag for a whole page
    without a deferred lazy-load per row.
    """
    if not asset_ids:
        return set()
    return set(
        session.execute(
            select(AssetEmbedding.asset_id).where(
                AssetEmbedding.asset_id.in_(asset_ids), AssetEmbedding.clip_embedding.is_not(None)
            )
        ).scalars()
    )


def load_all_semantic(session: Session) -> dict[int, np.ndarray]:
    """Map ``asset_id -> semantic vector`` for every asset that has one.

    The canonical source for rebuilding ``vec_asset_embedding``.
    """
    rows = session.execute(
        select(AssetEmbedding.asset_id, AssetEmbedding.clip_embedding).where(
            AssetEmbedding.clip_embedding.is_not(None)
        )
    ).all()
    return {int(asset_id): np.frombuffer(blob, dtype=_DTYPE) for asset_id, blob in rows if blob is not None}


def set_semantic(session: Session, asset_id: int, embedding: np.ndarray) -> None:
    """Persist the asset's semantic embedding (no commit — caller owns the tx)."""
    _upsert_column(session, asset_id, "clip_embedding", _to_blob(embedding))


# ----------------------------------------------------------------------------
# Visual space (DINOv2, P37) — canonical vector behind vec_asset_dino
# ----------------------------------------------------------------------------


def get_visual(session: Session, asset_id: int) -> np.ndarray | None:
    """Return the asset's visual (DINOv2) embedding, or ``None``.

    A missing visual embedding is a valid state (ADR-024) — ``None`` here also
    covers a missing asset, matching every current caller's degrade-to-SigLIP2 path.
    """
    blob = session.execute(
        select(AssetEmbedding.dino_embedding).where(AssetEmbedding.asset_id == asset_id)
    ).scalar_one_or_none()
    return _to_vector(blob)


def load_visual(session: Session, asset_ids: Sequence[int]) -> dict[int, np.ndarray]:
    """Map ``asset_id -> visual vector`` for the subset of *asset_ids* that has one.

    Assets without a DINOv2 embedding (a valid state, ADR-024) are simply absent
    from the result. Fetches *by id*, not by nearest-neighbour — the vec0 index is
    for KNN, this is for "give me these specific vectors".
    """
    if not asset_ids:
        return {}
    rows = session.execute(
        select(AssetEmbedding.asset_id, AssetEmbedding.dino_embedding).where(
            AssetEmbedding.asset_id.in_(asset_ids), AssetEmbedding.dino_embedding.is_not(None)
        )
    ).all()
    return {int(asset_id): np.frombuffer(blob, dtype=_DTYPE) for asset_id, blob in rows if blob is not None}


def load_all_visual(session: Session) -> dict[int, np.ndarray]:
    """Map ``asset_id -> visual vector`` for every asset that has one.

    Whole-library scan for the pairwise dupe scan (and any future rebuild of
    ``vec_asset_dino``).
    """
    rows = session.execute(
        select(AssetEmbedding.asset_id, AssetEmbedding.dino_embedding).where(
            AssetEmbedding.dino_embedding.is_not(None)
        )
    ).all()
    return {int(asset_id): np.frombuffer(blob, dtype=_DTYPE) for asset_id, blob in rows if blob is not None}


def set_visual(session: Session, asset_id: int, embedding: np.ndarray) -> None:
    """Persist the asset's visual embedding (no commit — caller owns the tx)."""
    _upsert_column(session, asset_id, "dino_embedding", _to_blob(embedding))
