"""Semantic search endpoint — text→image and image→image over the CLIP vector index.

`POST /api/search/semantic` accepts either a free-text `query` (embedded on the
fly via the CLIP text encoder) or a `like_asset_id` (reuses that asset's stored
embedding). Returns the most similar *active* assets with cosine scores (ADR-001).
"""
from __future__ import annotations

import asyncio
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from photofant.db import vector_index
from photofant.db.models import Asset, AssetInstance
from photofant.db.session import get_session

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


def _embed_query_text(query: str) -> np.ndarray:
    from photofant.inference.adapters.clip import resolve_clip_embedder

    embedder = resolve_clip_embedder()
    if embedder is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SEMANTIC_SEARCH_UNAVAILABLE",
                "message": "CLIP-Modell ist nicht aktiv — Textsuche nicht möglich.",
            },
        )
    return embedder.embed_text(query)


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

    exclude_id: int | None = None
    if has_query:
        query_text: str = body.query.strip()  # type: ignore[union-attr]
        query_embedding = await asyncio.to_thread(_embed_query_text, query_text)
    else:
        exclude_id = body.like_asset_id
        query_embedding = _embedding_for_asset(session, body.like_asset_id)  # type: ignore[arg-type]

    candidate_count = max(body.limit * _CANDIDATE_FACTOR, body.limit + _CANDIDATE_FLOOR)
    candidates = vector_index.search(session, query_embedding, candidate_count)

    candidate_ids = [asset_id for asset_id, _ in candidates if asset_id != exclude_id]
    active = _active_asset_ids(session, candidate_ids)

    hits: list[SearchHit] = []
    for asset_id, score in candidates:
        if asset_id == exclude_id or asset_id not in active:
            continue
        hits.append(SearchHit(asset_id=asset_id, score=score))
        if len(hits) == body.limit:
            break

    return SemanticSearchResponse(hits=hits)
