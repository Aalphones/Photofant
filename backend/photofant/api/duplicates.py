"""Duplicates API — pHash-based duplicate search within a person's assets.

POST /duplicates/search  → { person_id, threshold } → DupePairDto[]
"""
from __future__ import annotations

import logging
from typing import Annotated

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


class DupeSearchRequest(BaseModel):
    person_id: int
    threshold: int = _DEFAULT_THRESHOLD


class DupePairDto(BaseModel):
    asset_a_id: int
    asset_b_id: int
    asset_a_content_hash: str
    asset_b_content_hash: str
    phash_distance: int
    similarity_pct: int


@router.post("/search", response_model=list[DupePairDto])
async def search_person_duplicates(
    body: DupeSearchRequest,
    session: DbSession,
) -> list[DupePairDto]:
    """Find duplicate pairs among a person's assets using pHash Hamming distance."""
    person = session.get(Person, body.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    threshold = max(0, min(body.threshold, _MAX_THRESHOLD))

    rows = session.execute(
        select(AssetInstance.asset_id, Asset.phash, Asset.content_hash)
        .join(Asset, Asset.id == AssetInstance.asset_id)
        .where(
            AssetInstance.person_id == body.person_id,
            AssetInstance.deleted_at.is_(None),
            Asset.phash.is_not(None),
        )
    ).all()

    if len(rows) < 2:
        return []

    asset_data = [(int(row[0]), int(row[1]), str(row[2])) for row in rows]
    hash_by_id: dict[int, str] = {row[0]: row[2] for row in asset_data}

    pairs: list[DupePairDto] = []
    seen: set[tuple[int, int]] = set()

    for i in range(len(asset_data)):
        for j in range(i + 1, len(asset_data)):
            id_a, phash_a, _ = asset_data[i]
            id_b, phash_b, _ = asset_data[j]

            distance = hamming_distance(phash_a, phash_b)
            if distance > threshold:
                continue

            key = (min(id_a, id_b), max(id_a, id_b))
            if key in seen:
                continue
            seen.add(key)

            similarity_pct = round((1.0 - distance / 64.0) * 100)
            pairs.append(DupePairDto(
                asset_a_id=key[0],
                asset_b_id=key[1],
                asset_a_content_hash=hash_by_id[key[0]],
                asset_b_content_hash=hash_by_id[key[1]],
                phash_distance=distance,
                similarity_pct=similarity_pct,
            ))

    pairs.sort(key=lambda pair: pair.phash_distance)
    return pairs
