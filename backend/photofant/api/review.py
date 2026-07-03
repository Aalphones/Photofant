"""Review API — duplicate pairs and ad-hoc similarity search."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, cast

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import ColumnElement, exists, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, aliased
from sqlalchemy.orm.attributes import InstrumentedAttribute

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


class DupePageDto(BaseModel):
    items: list[DupePairDto]
    total: int


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


def _has_active_instance(asset_id_column: InstrumentedAttribute[int]) -> ColumnElement[bool]:
    return exists(
        select(AssetInstance.id).where(
            AssetInstance.asset_id == asset_id_column,
            AssetInstance.deleted_at.is_(None),
        )
    )


def _auto_resolve_trashed_pairs(session: Session) -> None:
    """Bulk-resolve unresolved pairs whose asset_a or asset_b has no active instance left.

    Single UPDATE with correlated EXISTS subqueries — replaces the former per-row
    2-COUNT-queries-in-Python loop that caused >111k queries on a large backlog.
    """
    result = cast(
        "CursorResult[Any]",
        session.execute(
            update(ReviewItem)
            .where(
                ReviewItem.type == "dupe_candidate",
                ReviewItem.resolved_at.is_(None),
                ~(_has_active_instance(ReviewItem.asset_a_id) & _has_active_instance(ReviewItem.asset_b_id)),
            )
            .values(resolved_at=_now_utc(), resolution="auto_trashed")
        ),
    )
    if result.rowcount:
        log.info("auto-resolved %d dupe pairs (asset in trash)", result.rowcount)
        session.commit()


@router.get("/review/dupes", response_model=DupePageDto)
async def list_dupe_pairs(session: DbSession, offset: int = 0, limit: int = 50) -> DupePageDto:
    """Return a page of unresolved dupe-candidate pairs with full asset data on both sides.

    Actionable-first sort: exact pHash matches before CLIP-only matches, then by distance.
    """
    offset = max(offset, 0)
    limit = min(max(limit, 1), 200)

    _auto_resolve_trashed_pairs(session)

    asset_a = aliased(Asset)
    asset_b = aliased(Asset)
    base_filters = (
        ReviewItem.type == "dupe_candidate",
        ReviewItem.resolved_at.is_(None),
    )
    # INNER JOIN on both sides: a review_item whose asset_b (or asset_a) no longer
    # exists is silently excluded, instead of the former warn-and-skip in Python.
    joined = (
        select(ReviewItem, asset_a, asset_b)
        .join(asset_a, asset_a.id == ReviewItem.asset_a_id)
        .join(asset_b, asset_b.id == ReviewItem.asset_b_id)
        .where(*base_filters)
    )

    total: int = session.scalar(
        select(func.count()).select_from(joined.with_only_columns(ReviewItem.id).subquery())
    ) or 0

    rows = session.execute(
        joined
        .order_by(
            ReviewItem.phash_distance.is_(None),
            ReviewItem.phash_distance,
            ReviewItem.clip_distance,
            ReviewItem.id,
        )
        .offset(offset)
        .limit(limit)
    ).all()

    items = [_to_pair_dto(item, row_asset_a, row_asset_b) for item, row_asset_a, row_asset_b in rows]
    return DupePageDto(items=items, total=total)


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
