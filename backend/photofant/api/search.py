"""Semantic search endpoints — text→image, image→image and upload→image over the
embedding vector index.

`POST /api/search/semantic` accepts either a free-text `query` (embedded on the
fly via the active image embedder's text encoder) or a `like_asset_id` (reuses
that asset's stored embedding). `POST /api/search/by-image` embeds an *uploaded*
image (P36 reverse image search) — the upload is never saved/imported, only
embedded. Both return the most similar *active* assets with cosine scores
(ADR-001). The concrete model is resolved by capability (ADR-022).
"""
from __future__ import annotations

import asyncio
import io
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from photofant.db import vector_index
from photofant.db.models import Asset, AssetInstance
from photofant.db.session import get_session
from photofant.inference.interfaces import Embedder, TextEmbedder
from photofant.search.rerank import rerank_by_appearance
from photofant.settings import load_settings

router = APIRouter(prefix="/search")

DbSession = Annotated[Session, Depends(get_session)]

# Over-fetch from the index so soft-deleted hits can be filtered without
# starving the requested page.
_CANDIDATE_FACTOR = 4
_CANDIDATE_FLOOR = 20


class SemanticSearchRequest(BaseModel):
    query: str | None = None
    like_asset_id: int | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 24


class SearchHit(BaseModel):
    asset_id: int
    score: float


class SemanticSearchResponse(BaseModel):
    hits: list[SearchHit]


def _require_embedder(unavailable_message: str) -> Embedder:
    from photofant.inference.image_embedder import resolve_image_embedder

    embedder = resolve_image_embedder()
    if embedder is None:
        raise HTTPException(
            status_code=409,
            detail={"code": "SEMANTIC_SEARCH_UNAVAILABLE", "message": unavailable_message},
        )
    return embedder


def _embed_query_text(query: str) -> np.ndarray:
    embedder = _require_embedder("Kein Bild-Embedder aktiv — Textsuche nicht möglich.")
    if not isinstance(embedder, TextEmbedder):
        # The active image embedder is visual-only (e.g. DINOv2) — it can't embed
        # a text query. Should not happen for role "semantic_search", but the seam
        # is honest about it rather than crashing on a missing method.
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SEMANTIC_SEARCH_UNAVAILABLE",
                "message": "Aktiver Bild-Embedder kann keine Textsuche.",
            },
        )
    return embedder.embed_text(query)


def _decode_upload(content: bytes) -> np.ndarray:
    """Decode raw upload bytes into a uint8 RGB array. Raises 422 if unreadable."""
    try:
        with Image.open(io.BytesIO(content)) as raw:
            return np.array(raw.convert("RGB"), dtype=np.uint8)
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_IMAGE", "message": "Datei ist kein lesbares Bild."},
        ) from error


def _embedding_for_asset(session: Session, asset_id: int) -> np.ndarray:
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.clip_embedding is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "NO_EMBEDDING",
                "message": "Für dieses Bild liegt noch kein Embedding vor.",
            },
        )
    return np.frombuffer(asset.clip_embedding, dtype=np.float32)


def _dino_embedding_for_asset(session: Session, asset_id: int) -> np.ndarray | None:
    """Return the stored DINOv2 vector of *asset_id*, or None if it has none.

    A missing DINOv2 embedding is a valid state (ADR-024) — the caller then skips
    re-ranking and keeps the plain SigLIP2 order. Never raises for the missing case.
    """
    asset = session.get(Asset, asset_id)
    if asset is None or asset.dino_embedding is None:
        return None
    return np.frombuffer(asset.dino_embedding, dtype=np.float32)


def _embed_upload_dino(image: np.ndarray) -> np.ndarray | None:
    """Embed an uploaded image with the active visual-rerank (DINOv2) embedder.

    Returns None when no DINOv2 model is enabled — re-ranking then degrades to the
    plain SigLIP2 order. This is the one place the *upload* path needs the DINOv2
    model live, since the query image has no precomputed vector.
    """
    from photofant.inference.image_embedder import resolve_image_embedder

    dino_embedder = resolve_image_embedder(role="visual_rerank")
    if dino_embedder is None:
        return None
    return dino_embedder.embed(image)


def _rerank_pool(
    session: Session,
    query_dino_vec: np.ndarray,
    ordered: list[tuple[int, float]],
    limit: int,
) -> list[tuple[int, float]]:
    """Re-order an active-filtered candidate pool by DINOv2 appearance.

    Candidates with a DINOv2 vector come first, sorted by visual similarity (their
    score becomes the DINOv2 cosine). Candidates without a vector are appended in
    their original SigLIP2 order so the result never shrinks. Truncated to *limit*.
    """
    candidate_ids = [asset_id for asset_id, _ in ordered]
    reranked = rerank_by_appearance(session, query_dino_vec, candidate_ids, top_k=len(candidate_ids))
    reranked_ids = {asset_id for asset_id, _ in reranked}
    tail = [(asset_id, score) for asset_id, score in ordered if asset_id not in reranked_ids]
    return (reranked + tail)[:limit]


def _active_asset_ids(session: Session, asset_ids: list[int]) -> set[int]:
    if not asset_ids:
        return set()
    rows = (
        session.query(AssetInstance.asset_id)
        .filter(AssetInstance.asset_id.in_(asset_ids))
        .filter(AssetInstance.deleted_at.is_(None))
        .all()
    )
    return {row[0] for row in rows}


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(body: SemanticSearchRequest, session: DbSession) -> SemanticSearchResponse:
    has_query = bool(body.query and body.query.strip())
    has_like = body.like_asset_id is not None
    if has_query == has_like:
        raise HTTPException(
            status_code=422,
            detail="Provide exactly one of 'query' or 'like_asset_id'.",
        )

    rerank_settings = load_settings()["rerank"]

    exclude_id: int | None = None
    query_dino_vec: np.ndarray | None = None
    if has_query:
        # Text→image: DINOv2 has no text encoder, so re-ranking never fires here —
        # the SigLIP2 order stands (ADR-024).
        query_text: str = body.query.strip()  # type: ignore[union-attr]
        query_embedding = await asyncio.to_thread(_embed_query_text, query_text)
    else:
        exclude_id = body.like_asset_id
        query_embedding = _embedding_for_asset(session, body.like_asset_id)  # type: ignore[arg-type]
        if rerank_settings["enabled"]:
            query_dino_vec = _dino_embedding_for_asset(session, body.like_asset_id)  # type: ignore[arg-type]

    candidate_count = max(body.limit * _CANDIDATE_FACTOR, body.limit + _CANDIDATE_FLOOR)
    if query_dino_vec is not None:
        candidate_count = max(candidate_count, rerank_settings["candidate_pool_size"])
    candidates = vector_index.search(session, query_embedding, candidate_count)

    candidate_ids = [asset_id for asset_id, _ in candidates if asset_id != exclude_id]
    active = _active_asset_ids(session, candidate_ids)
    ordered = [
        (asset_id, score)
        for asset_id, score in candidates
        if asset_id != exclude_id and asset_id in active
    ]

    if query_dino_vec is not None:
        ordered = _rerank_pool(session, query_dino_vec, ordered, body.limit)

    hits = [SearchHit(asset_id=asset_id, score=score) for asset_id, score in ordered[: body.limit]]
    return SemanticSearchResponse(hits=hits)


@router.post("/by-image", response_model=SemanticSearchResponse)
async def search_by_image(
    session: DbSession,
    file: Annotated[UploadFile, File()],
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> SemanticSearchResponse:
    """Embed an uploaded image and return the most similar library assets (P36).

    The upload is decoded in memory and embedded — never written to disk or
    imported. `limit` defaults to `reverseSearch.similarLimit`.
    """
    reverse_search = load_settings()["reverse_search"]
    effective_limit = limit or reverse_search["similar_limit"]
    max_bytes = reverse_search["max_upload_bytes"]

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "UPLOAD_TOO_LARGE",
                "message": f"Bild ist zu groß (max. {max_bytes // (1024 * 1024)} MB).",
            },
        )

    embedder = _require_embedder("Kein Bild-Embedder aktiv — Reverse-Suche nicht möglich.")
    image = _decode_upload(content)
    query_embedding = await asyncio.to_thread(embedder.embed, image)

    rerank_settings = load_settings()["rerank"]
    query_dino_vec: np.ndarray | None = None
    if rerank_settings["enabled"]:
        # Upload has no precomputed DINOv2 vector — embed it on the fly. None means
        # no DINOv2 model is active, so re-ranking degrades to the SigLIP2 order.
        query_dino_vec = await asyncio.to_thread(_embed_upload_dino, image)

    min_score = reverse_search["min_score"]
    candidate_count = max(effective_limit * _CANDIDATE_FACTOR, effective_limit + _CANDIDATE_FLOOR)
    if query_dino_vec is not None:
        candidate_count = max(candidate_count, rerank_settings["candidate_pool_size"])
    candidates = vector_index.search(session, query_embedding, candidate_count)
    candidate_ids = [asset_id for asset_id, _ in candidates]
    active = _active_asset_ids(session, candidate_ids)

    # Apply the SigLIP2 score floor before re-ranking — min_score is a SigLIP-space
    # threshold, so it must gate the candidate pool, not the DINOv2 order.
    ordered = [
        (asset_id, score)
        for asset_id, score in candidates
        if asset_id in active and score >= min_score
    ]

    if query_dino_vec is not None:
        ordered = _rerank_pool(session, query_dino_vec, ordered, effective_limit)

    hits = [
        SearchHit(asset_id=asset_id, score=score) for asset_id, score in ordered[:effective_limit]
    ]
    return SemanticSearchResponse(hits=hits)
