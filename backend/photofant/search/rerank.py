"""DINOv2 visual re-ranking of image→image search candidates (P37, ADR-024).

Two-stage retrieval: SigLIP2 K-NN finds a pool of thematically similar candidates,
then this module re-orders that pool by *visual appearance* (DINOv2) so images that
actually look alike — same composition, perspective, colour, style — rise to the top.

The heavy lifting is `_rank_by_cosine`, a pure function over already-loaded vectors
(unit-tested without a DB). `rerank_by_appearance` is the thin public seam: it loads
the candidates' DINOv2 vectors via the vector index and hands them to the ranker.

Degradation is the caller's job (api/search.py): re-ranking only ever fires when a
query *image* exists and a DINOv2 vector is available. Given no candidate has a
DINOv2 vector, this returns an empty list and the caller keeps the SigLIP2 order.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sqlalchemy.orm import Session

from photofant.db import vector_index


def _rank_by_cosine(
    query_vec: np.ndarray,
    candidate_vectors: dict[int, np.ndarray],
    top_k: int,
) -> list[tuple[int, float]]:
    """Sort *candidate_vectors* by cosine similarity to *query_vec*, best first.

    Pure and DB-free. Vectors are stored L2-normalised, but we normalise
    defensively so a stray un-normalised input can't silently skew the order.
    Returns at most *top_k* (id, score) pairs; an empty candidate map yields [].
    """
    if not candidate_vectors or top_k <= 0:
        return []

    query_norm = _unit(query_vec)
    scored: list[tuple[int, float]] = []
    for asset_id, vector in candidate_vectors.items():
        similarity = float(np.dot(query_norm, _unit(vector)))
        scored.append((asset_id, similarity))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]


def _unit(vector: np.ndarray) -> np.ndarray:
    """Return the unit-norm version of a 1-D vector (guards the zero vector)."""
    flat = np.ascontiguousarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(flat))
    if norm == 0.0:
        return flat
    return flat / norm


def rerank_by_appearance(
    session: Session,
    query_dino_vec: np.ndarray,
    candidate_asset_ids: Sequence[int],
    top_k: int,
) -> list[tuple[int, float]]:
    """Re-rank *candidate_asset_ids* by DINOv2 appearance similarity to the query.

    Loads the DINOv2 vectors of the candidates and orders them by cosine to
    *query_dino_vec*, best first. Only candidates that actually have a DINOv2
    vector are ranked; the rest are absent from the result (the caller appends
    them in their original SigLIP2 order). Returns at most *top_k* pairs.
    """
    candidate_vectors = vector_index.load_dino_embeddings(session, candidate_asset_ids)
    return _rank_by_cosine(query_dino_vec, candidate_vectors, top_k)
