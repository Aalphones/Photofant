"""Review API — duplicate pairs and ad-hoc similarity search."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from photofant.config import get_data_root
from photofant.db import vector_index
from photofant.db.models import Asset, AssetInstance, ReviewItem
from photofant.db.session import get_session
from photofant.media.phash import find_similar

log = logging.getLogger(__name__)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]

DupeResolution = Literal["a_is_original", "b_is_original", "delete_a", "delete_b", "dismiss"]


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AssetSummaryDto(BaseModel):
    id: int
    content_hash: str
    width: int | None
    height: int | None
    format: str | None
    source: str | None
    file_size: int | None
    created_at: datetime | None
    imported_at: datetime | None


class DupePairDto(BaseModel):
    id: int
    asset_a: AssetSummaryDto
    asset_b: AssetSummaryDto
    # Nullable: pairs found by only one method have no distance from the other.
    phash_distance: int | None
    phash_similarity_pct: int | None
    clip_distance: float | None
    clip_similarity_pct: int | None
    triggered_by: Literal["phash", "clip", "both"]
    created_at: datetime


class SimilarAssetDto(AssetSummaryDto):
    phash_distance: int | None = None
    clip_distance: float | None = None
    clip_similarity_pct: int | None = None


class ResolveRequest(BaseModel):
    resolution: DupeResolution


def _to_summary(asset: Asset) -> AssetSummaryDto:
    return AssetSummaryDto(
        id=asset.id,
        content_hash=asset.content_hash,
        width=asset.width,
        height=asset.height,
        format=asset.format,
        source=asset.source,
        file_size=asset.file_size,
        created_at=asset.created_at,
        imported_at=asset.imported_at,
    )


def _to_pair_dto(item: ReviewItem, asset_a: Asset, asset_b: Asset) -> DupePairDto:
    phash_similarity_pct = (
        round((1.0 - item.phash_distance / 64.0) * 100) if item.phash_distance is not None else None
    )
    clip_similarity_pct = (
        round((1.0 - item.clip_distance) * 100) if item.clip_distance is not None else None
    )
    triggered_by: Literal["phash", "clip", "both"] = (
        "both"  if item.phash_distance is not None and item.clip_distance is not None else
        "phash" if item.phash_distance is not None else
        "clip"
    )
    return DupePairDto(
        id=item.id,
        asset_a=_to_summary(asset_a),
        asset_b=_to_summary(asset_b),
        phash_distance=item.phash_distance,
        phash_similarity_pct=phash_similarity_pct,
        clip_distance=item.clip_distance,
        clip_similarity_pct=clip_similarity_pct,
        triggered_by=triggered_by,
        created_at=item.created_at,
    )


@router.get("/review/dupes", response_model=list[DupePairDto])
async def list_dupe_pairs(session: DbSession) -> list[DupePairDto]:
    """Return all unresolved dupe-candidate pairs with full asset data on both sides."""
    # Join only asset_a; asset_b loaded via identity-map (single extra SELECT per missing item).
    rows = (
        session.query(ReviewItem, Asset)
        .join(Asset, Asset.id == ReviewItem.asset_a_id)
        .filter(ReviewItem.type == "dupe_candidate")
        .filter(ReviewItem.resolved_at.is_(None))
        .order_by(ReviewItem.phash_distance, ReviewItem.id)
        .all()
    )
    result: list[DupePairDto] = []
    auto_resolved: list[ReviewItem] = []

    for item, asset_a in rows:
        asset_b = session.get(Asset, item.asset_b_id)
        if asset_b is None:
            log.warning("review_item %d references missing asset_b %d — skipping", item.id, item.asset_b_id)
            continue

        a_active: int = session.scalar(
            select(func.count())
            .select_from(AssetInstance)
            .where(AssetInstance.asset_id == asset_a.id, AssetInstance.deleted_at.is_(None))
        ) or 0
        b_active: int = session.scalar(
            select(func.count())
            .select_from(AssetInstance)
            .where(AssetInstance.asset_id == asset_b.id, AssetInstance.deleted_at.is_(None))
        ) or 0

        if a_active == 0 or b_active == 0:
            log.info(
                "review_item %d auto-resolved: asset_a active=%d asset_b active=%d (in trash)",
                item.id, a_active, b_active,
            )
            item.resolved_at = _now_utc()
            item.resolution = "auto_trashed"
            auto_resolved.append(item)
            continue

        result.append(_to_pair_dto(item, asset_a, asset_b))

    if auto_resolved:
        session.commit()

    return result


@router.patch("/review/dupes/{item_id}", response_model=DupePairDto)
async def resolve_dupe(item_id: int, body: ResolveRequest, session: DbSession) -> DupePairDto:
    """Resolve a dupe-candidate pair with the given action."""
    item = session.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found")

    asset_a = session.get(Asset, item.asset_a_id)
    asset_b = session.get(Asset, item.asset_b_id)
    if asset_a is None or asset_b is None:
        raise HTTPException(status_code=404, detail="Referenced asset not found")

    resolution = body.resolution

    if resolution == "a_is_original":
        asset_b.original_id = asset_a.id
    elif resolution == "b_is_original":
        asset_a.original_id = asset_b.id
    elif resolution in ("delete_a", "delete_b"):
        from photofant.media import moves
        data_root = get_data_root()
        target_asset = asset_a if resolution == "delete_a" else asset_b
        instance = session.execute(
            select(AssetInstance)
            .where(AssetInstance.asset_id == target_asset.id)
            .where(AssetInstance.deleted_at.is_(None))
        ).scalar_one_or_none()
        if instance is None:
            log.info(
                "resolve_dupe %d (%s): asset %d already in trash — marking resolved without move",
                item_id, resolution, target_asset.id,
            )
        else:
            await moves.soft_delete(session, instance, data_root)
    # dismiss: no asset modification

    item.resolved_at = _now_utc()
    item.resolution = resolution
    session.commit()
    session.refresh(asset_a)
    session.refresh(asset_b)
    session.refresh(item)

    return _to_pair_dto(item, asset_a, asset_b)


@dataclass
class _SimilarMatch:
    """Per-asset distances found by each method — UNION merge, like the scan job."""
    phash_distance: int | None = None
    clip_distance: float | None = None


@router.get("/assets/{asset_id}/similar", response_model=list[SimilarAssetDto])
async def get_similar_assets(asset_id: int, session: DbSession) -> list[SimilarAssetDto]:
    """Return assets similar to the given one (ad-hoc pHash + CLIP search, for Lightbox)."""
    from photofant.settings import load_settings

    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    settings = load_settings()
    phash_enabled: bool = settings["dupe_phash_enabled"]
    clip_enabled: bool = settings["dupe_clip_enabled"]
    clip_threshold: float = settings["similar_clip_threshold"]

    matches: dict[int, _SimilarMatch] = {}

    if phash_enabled and asset.phash is not None:
        for similar_id, distance in find_similar(session, asset.phash, asset_id, 0):
            matches.setdefault(similar_id, _SimilarMatch()).phash_distance = distance

    if clip_enabled and asset.clip_embedding is not None:
        query_embedding = np.frombuffer(asset.clip_embedding, dtype=np.float32)
        for similar_id, cosine_similarity in vector_index.search(session, query_embedding, limit=20):
            if similar_id == asset_id:
                continue
            clip_distance = 1.0 - cosine_similarity
            if clip_distance > clip_threshold:
                continue
            matches.setdefault(similar_id, _SimilarMatch()).clip_distance = clip_distance

    result: list[SimilarAssetDto] = []
    for similar_id, match in matches.items():
        similar_asset = session.get(Asset, similar_id)
        if similar_asset is None:
            continue
        clip_similarity_pct = (
            round((1.0 - match.clip_distance) * 100) if match.clip_distance is not None else None
        )
        result.append(SimilarAssetDto(
            **_to_summary(similar_asset).model_dump(),
            phash_distance=match.phash_distance,
            clip_distance=match.clip_distance,
            clip_similarity_pct=clip_similarity_pct,
        ))

    def _best_score(dto: SimilarAssetDto) -> float:
        # Normalize pHash (0-64) onto the same 0-1 scale as CLIP cosine-distance
        # so the UNION can be sorted by "best" match regardless of which method found it.
        candidates = [
            value for value in (
                dto.phash_distance / 64 if dto.phash_distance is not None else None,
                dto.clip_distance,
            )
            if value is not None
        ]
        return min(candidates) if candidates else 1.0

    result.sort(key=_best_score)
    return result
