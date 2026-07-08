"""Duplicates API — DINOv2 duplicate search within a person's assets (ADR-007, ADR-018, ADR-024).

Ran on CLIP/SigLIP2 through P36; P37 Phase 4 moved the signal to DINOv2 (visual
appearance is what defines a duplicate). Field/param names keep the `clip_`
prefix for frontend/API compat — only the embedding source and threshold changed.

POST /duplicates/search  → { person_id, clip_threshold } → DupePairDto[]
"""
from __future__ import annotations

import logging
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import Asset, AssetInstance, Person
from photofant.db.session import get_session

log = logging.getLogger(__name__)

router = APIRouter(prefix="/duplicates")

DbSession = Annotated[Session, Depends(get_session)]

_MIN_DINO_THRESHOLD = 0.01
_MAX_DINO_THRESHOLD = 0.40


class DupeSearchRequest(BaseModel):
    person_id: int
    # None = use the current dupe_dino_threshold setting (avoids hardcoding a stale default).
    clip_threshold: float | None = None


class DupePairDto(BaseModel):
    asset_a_id: int
    asset_b_id: int
    asset_a_content_hash: str
    asset_b_content_hash: str
    clip_distance: float
    clip_similarity_pct: int
    similarity_pct: int  # == clip_similarity_pct


@router.post("/search", response_model=list[DupePairDto])
async def search_person_duplicates(
    body: DupeSearchRequest,
    session: DbSession,
) -> list[DupePairDto]:
    """Find duplicate pairs among a person's assets via DINOv2 embeddings (ADR-018, ADR-024)."""
    from photofant.settings import load_settings

    person = session.get(Person, body.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    settings = load_settings()
    clip_threshold_input = (
        body.clip_threshold if body.clip_threshold is not None else settings["dupe_dino_threshold"]
    )
    clip_threshold = max(_MIN_DINO_THRESHOLD, min(clip_threshold_input, _MAX_DINO_THRESHOLD))

    rows = session.execute(
        select(AssetInstance.asset_id, Asset.content_hash, Asset.dino_embedding)
        .join(Asset, Asset.id == AssetInstance.asset_id)
        .where(
            AssetInstance.person_id == body.person_id,
            AssetInstance.deleted_at.is_(None),
        )
    ).all()

    if len(rows) < 2:
        return []

    hash_by_id: dict[int, str] = {int(row[0]): str(row[1]) for row in rows}

    dino_assets = [(int(row[0]), bytes(row[2])) for row in rows if row[2] is not None]

    pairs: list[DupePairDto] = []
    if len(dino_assets) >= 2:
        asset_ids = [asset_id for asset_id, _ in dino_assets]
        vectors = np.stack([np.frombuffer(blob, dtype=np.float32) for _, blob in dino_assets])
        similarities = vectors @ vectors.T
        for i in range(len(asset_ids)):
            for j in range(i + 1, len(asset_ids)):
                clip_distance = float(1.0 - similarities[i, j])
                if clip_distance > clip_threshold:
                    continue
                asset_a_id, asset_b_id = min(asset_ids[i], asset_ids[j]), max(asset_ids[i], asset_ids[j])
                clip_similarity_pct = round((1.0 - clip_distance) * 100)
                pairs.append(DupePairDto(
                    asset_a_id=asset_a_id,
                    asset_b_id=asset_b_id,
                    asset_a_content_hash=hash_by_id[asset_a_id],
                    asset_b_content_hash=hash_by_id[asset_b_id],
                    clip_distance=clip_distance,
                    clip_similarity_pct=clip_similarity_pct,
                    similarity_pct=clip_similarity_pct,
                ))

    pairs.sort(key=lambda pair: -pair.similarity_pct)
    return pairs
