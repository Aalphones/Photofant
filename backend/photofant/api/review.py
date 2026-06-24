"""Review API — duplicate pairs and ad-hoc similarity search."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from photofant.config import get_data_root
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
    phash_distance: int
    created_at: datetime


class SimilarAssetDto(AssetSummaryDto):
    phash_distance: int


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
    return DupePairDto(
        id=item.id,
        asset_a=_to_summary(asset_a),
        asset_b=_to_summary(asset_b),
        phash_distance=item.phash_distance,
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


@router.get("/assets/{asset_id}/similar", response_model=list[SimilarAssetDto])
async def get_similar_assets(asset_id: int, session: DbSession) -> list[SimilarAssetDto]:
    """Return assets similar to the given one (ad-hoc pHash search, for Lightbox)."""
    from photofant.settings import load_settings

    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.phash is None:
        return []

    settings = load_settings()
    threshold: int = settings["dupe_threshold"]

    similar_pairs = find_similar(session, asset.phash, asset_id, threshold)

    result: list[SimilarAssetDto] = []
    for similar_id, distance in similar_pairs:
        similar_asset = session.get(Asset, similar_id)
        if similar_asset is None:
            continue
        result.append(SimilarAssetDto(
            **_to_summary(similar_asset).model_dump(),
            phash_distance=distance,
        ))
    return result
