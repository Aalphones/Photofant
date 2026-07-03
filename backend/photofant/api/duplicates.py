"""Duplicates API — pHash + CLIP duplicate search within a person's assets (OR-logic, ADR-007).

POST /duplicates/search  → { person_id, threshold, clip_threshold } → DupePairDto[]
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import Asset, AssetInstance, Person
from photofant.db.session import get_session
from photofant.media.phash import hamming_distance

log = logging.getLogger(__name__)

router = APIRouter(prefix="/duplicates")

DbSession = Annotated[Session, Depends(get_session)]

_MAX_THRESHOLD = 32
_DEFAULT_THRESHOLD = 10
_MIN_CLIP_THRESHOLD = 0.01
_MAX_CLIP_THRESHOLD = 0.30


class DupeSearchRequest(BaseModel):
    person_id: int
    threshold: int = _DEFAULT_THRESHOLD
    # None = use the current dupe_clip_threshold setting (avoids hardcoding a stale default).
    clip_threshold: float | None = None


class DupePairDto(BaseModel):
    asset_a_id: int
    asset_b_id: int
    asset_a_content_hash: str
    asset_b_content_hash: str
    # Nullable: pairs found by only one method have no distance from the other.
    phash_distance: int | None
    phash_similarity_pct: int | None
    clip_distance: float | None
    clip_similarity_pct: int | None
    similarity_pct: int  # max(phash_similarity_pct, clip_similarity_pct)
    triggered_by: Literal["phash", "clip", "both"]


@dataclass
class _PairMatch:
    """Per-pair distances found by each method — UNION merge, like the scan job."""
    phash_distance: int | None = None
    clip_distance: float | None = None


@router.post("/search", response_model=list[DupePairDto])
async def search_person_duplicates(
    body: DupeSearchRequest,
    session: DbSession,
) -> list[DupePairDto]:
    """Find duplicate pairs among a person's assets via pHash + CLIP (UNION, OR-logic, ADR-007)."""
    from photofant.settings import load_settings

    person = session.get(Person, body.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    settings = load_settings()
    threshold = max(0, min(body.threshold, _MAX_THRESHOLD))
    clip_threshold_input = (
        body.clip_threshold if body.clip_threshold is not None else settings["dupe_clip_threshold"]
    )
    clip_threshold = max(_MIN_CLIP_THRESHOLD, min(clip_threshold_input, _MAX_CLIP_THRESHOLD))
    clip_enabled: bool = settings["dupe_clip_enabled"]

    rows = session.execute(
        select(AssetInstance.asset_id, Asset.phash, Asset.content_hash, Asset.clip_embedding)
        .join(Asset, Asset.id == AssetInstance.asset_id)
        .where(
            AssetInstance.person_id == body.person_id,
            AssetInstance.deleted_at.is_(None),
        )
    ).all()

    if len(rows) < 2:
        return []

    hash_by_id: dict[int, str] = {int(row[0]): str(row[2]) for row in rows}

    # (asset_a_id, asset_b_id) -> distances found by each method; UNION merge, OR-logic.
    found: dict[tuple[int, int], _PairMatch] = {}

    phash_assets = [(int(row[0]), int(row[1])) for row in rows if row[1] is not None]
    for i in range(len(phash_assets)):
        for j in range(i + 1, len(phash_assets)):
            id_a, phash_a = phash_assets[i]
            id_b, phash_b = phash_assets[j]
            distance = hamming_distance(phash_a, phash_b)
            if distance > threshold:
                continue
            key = (min(id_a, id_b), max(id_a, id_b))
            found.setdefault(key, _PairMatch()).phash_distance = distance

    if clip_enabled:
        clip_assets = [(int(row[0]), bytes(row[3])) for row in rows if row[3] is not None]
        if len(clip_assets) >= 2:
            asset_ids = [asset_id for asset_id, _ in clip_assets]
            vectors = np.stack([np.frombuffer(blob, dtype=np.float32) for _, blob in clip_assets])
            similarities = vectors @ vectors.T
            for i in range(len(asset_ids)):
                for j in range(i + 1, len(asset_ids)):
                    clip_distance = float(1.0 - similarities[i, j])
                    if clip_distance > clip_threshold:
                        continue
                    key = (min(asset_ids[i], asset_ids[j]), max(asset_ids[i], asset_ids[j]))
                    found.setdefault(key, _PairMatch()).clip_distance = clip_distance

    pairs: list[DupePairDto] = []
    for (asset_a_id, asset_b_id), match in found.items():
        phash_similarity_pct = (
            round((1.0 - match.phash_distance / 64.0) * 100) if match.phash_distance is not None else None
        )
        clip_similarity_pct = (
            round((1.0 - match.clip_distance) * 100) if match.clip_distance is not None else None
        )
        triggered_by: Literal["phash", "clip", "both"] = (
            "both"  if match.phash_distance is not None and match.clip_distance is not None else
            "phash" if match.phash_distance is not None else
            "clip"
        )
        similarity_pct = max(
            value for value in (phash_similarity_pct, clip_similarity_pct) if value is not None
        )
        pairs.append(DupePairDto(
            asset_a_id=asset_a_id,
            asset_b_id=asset_b_id,
            asset_a_content_hash=hash_by_id[asset_a_id],
            asset_b_content_hash=hash_by_id[asset_b_id],
            phash_distance=match.phash_distance,
            phash_similarity_pct=phash_similarity_pct,
            clip_distance=match.clip_distance,
            clip_similarity_pct=clip_similarity_pct,
            similarity_pct=similarity_pct,
            triggered_by=triggered_by,
        ))

    pairs.sort(key=lambda pair: -pair.similarity_pct)
    return pairs
