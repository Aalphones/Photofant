"""Collections endpoint — albums & smart albums (Konzept §10.1).

One album type with an optional smart mode: `kind = 'album'` is hand-curated,
`kind = 'smart_album'` is trigger-filled (and may still carry manual members). Toggling
the smart mode flips `kind`; turning it off drops the auto-materialized `source = 'smart'`
rows but keeps the hand-picked ones.
"""
from __future__ import annotations

import logging
from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.api.assets import TagDto
from photofant.collections.captions import CaptionAction
from photofant.collections.stats import compute_training_set_stats
from photofant.config import get_data_root
from photofant.db.models import (
    Asset,
    AssetInstance,
    AssetTag,
    Collection,
    CollectionItem,
    Person,
    SmartTrigger,
    Tag,
)
from photofant.db.session import get_session
from photofant.jobs.collections_job import (
    enqueue_reevaluate_collection,
)

router = APIRouter(prefix="/collections")

DbSession = Annotated[Session, Depends(get_session)]

log = logging.getLogger(__name__)

_VALID_KINDS = frozenset({"album", "smart_album", "training_set"})
_VALID_MATCH_MODES = frozenset({"any", "all"})
_VALID_TRIGGER_TYPES = frozenset({"person", "tag", "caption"})


class TriggerDto(BaseModel):
    id: int
    type: str
    person_id: int | None
    person_name: str | None
    tag_id: int | None
    tag_name: str | None
    phrase: str | None
    negate: bool


class CoverAssetDto(BaseModel):
    id: int
    content_hash: str


class TrainingSetSettings(BaseModel):
    trigger_word: str | None = None
    prefix: str | None = None
    suffix: str | None = None
    split_ratio: float | None = None  # Anteil Training (0.0-1.0), Rest = Val


class CollectionDto(BaseModel):
    id: int
    name: str
    kind: str
    match_mode: str
    member_count: int
    cover_assets: list[CoverAssetDto]
    description: str | None = None
    cover_asset_id: int | None = None
    settings: TrainingSetSettings | None = None


class CollectionDetailDto(CollectionDto):
    triggers: list[TriggerDto]
    item_order: list[int] = []  # asset ids, manuelle Reihenfolge (position ASC, dann id)


class CreateCollectionRequest(BaseModel):
    name: str
    kind: str = "album"
    match_mode: str = "any"


class UpdateCollectionRequest(BaseModel):
    name: str | None = None
    kind: str | None = None
    match_mode: str | None = None
    description: str | None = None
    cover_asset_id: int | None = None
    settings: TrainingSetSettings | None = None


class ReorderItemsRequest(BaseModel):
    asset_ids: list[int]  # gewünschte Reihenfolge, vollständige Mitgliederliste


class TrainingSetItemDto(BaseModel):
    id: int
    content_hash: str
    width: int | None
    height: int | None
    framing: str | None
    quality: float | None
    caption: str | None  # Original-Caption der Galerie (unangetastet)
    caption_override: str | None
    effective_caption: str | None  # override > original
    tags: list[TagDto]


class DistItemDto(BaseModel):
    value: str
    count: int


class TagFrequencyDto(BaseModel):
    name: str
    count: int


class HistogramBucketDto(BaseModel):
    label: str
    count: int


class TrainingSetStatsDto(BaseModel):
    total: int
    framing: list[DistItemDto]
    tag_frequencies: list[TagFrequencyDto]
    quality_histogram: list[HistogramBucketDto]
    ar_buckets: list[DistItemDto]
    near_dupe_rate: float


class UpdateItemCaptionRequest(BaseModel):
    caption_override: str | None = None


class CreateTriggerRequest(BaseModel):
    type: str
    person_id: int | None = None
    tag_id: int | None = None
    phrase: str | None = None
    negate: bool = False


class UpdateTriggerRequest(BaseModel):
    negate: bool


class AddItemsRequest(BaseModel):
    asset_ids: list[int]


class JobStarted(BaseModel):
    job_id: str


SidecarMode = Literal["tags", "caption", "both"]


class CollectionExportRequest(BaseModel):
    sidecar: SidecarMode | None = None
    split_ratio: float | None = None  # overrides settings.split_ratio when given
    target_dir: str | None = None


DupeResolution = Literal["keep_left", "keep_right", "keep_both"]

_DUPE_MAX_THRESHOLD = 0.5  # CLIP distance cap (1 - cosine similarity)


class CaptionActionRequest(BaseModel):
    action: CaptionAction
    params: dict[str, str] = {}


class CollectionDupePairDto(BaseModel):
    asset_a_id: int
    asset_b_id: int
    asset_a_content_hash: str
    asset_b_content_hash: str
    clip_distance: float
    similarity_pct: int


class ResolveDuplicateRequest(BaseModel):
    asset_a_id: int
    asset_b_id: int
    resolution: DupeResolution


def _member_asset_ids(session: Session, collection_id: int, limit: int | None = None) -> list[int]:
    """Active (non-deleted) member asset ids of a collection."""
    query = (
        session.query(CollectionItem.asset_id)
        .join(AssetInstance, AssetInstance.asset_id == CollectionItem.asset_id)
        .filter(CollectionItem.collection_id == collection_id, AssetInstance.deleted_at.is_(None))
        .distinct()
    )
    if limit is not None:
        query = query.limit(limit)
    return [row[0] for row in query.all()]


def _item_order(session: Session, collection_id: int) -> list[int]:
    """Active member asset ids ordered by manual `position` (NULL last), then id."""
    rows = (
        session.query(CollectionItem.asset_id)
        .join(AssetInstance, AssetInstance.asset_id == CollectionItem.asset_id)
        .filter(CollectionItem.collection_id == collection_id, AssetInstance.deleted_at.is_(None))
        .distinct()
        .order_by(CollectionItem.position.is_(None), CollectionItem.position.asc(), CollectionItem.asset_id.asc())
        .all()
    )
    return [row[0] for row in rows]


def _cover_assets(session: Session, collection: Collection) -> list[CoverAssetDto]:
    """Up to 4 cover assets (id + content_hash) for album thumbnail display.

    The explicitly chosen `cover_asset_id` (P10 Phase 1) comes first when set and still
    an active member; the remaining slots fill up with other members as before.
    """
    rows = (
        session.query(CollectionItem.asset_id, Asset.content_hash)
        .join(Asset, Asset.id == CollectionItem.asset_id)
        .join(AssetInstance, AssetInstance.asset_id == CollectionItem.asset_id)
        .filter(CollectionItem.collection_id == collection.id, AssetInstance.deleted_at.is_(None))
        .distinct()
        .limit(8)  # etwas Puffer, falls das Cover unter den ersten 4 nicht dabei ist
        .all()
    )
    covers = [CoverAssetDto(id=row[0], content_hash=row[1]) for row in rows]
    cover_id = collection.cover_asset_id
    if cover_id is not None:
        chosen = next((cover for cover in covers if cover.id == cover_id), None)
        if chosen is None:
            asset = session.get(Asset, cover_id)
            chosen = CoverAssetDto(id=asset.id, content_hash=asset.content_hash) if asset is not None else None
        if chosen is not None:
            covers = [chosen] + [cover for cover in covers if cover.id != cover_id]
    return covers[:4]


def _build_trigger_dto(session: Session, trigger: SmartTrigger) -> TriggerDto:
    tag_name: str | None = None
    if trigger.type == "tag" and trigger.tag_id is not None:
        tag = session.get(Tag, trigger.tag_id)
        tag_name = tag.name if tag is not None else None
    person_name: str | None = None
    if trigger.type == "person" and trigger.person_id is not None:
        person = session.get(Person, trigger.person_id)
        person_name = person.name if person is not None else None
    return TriggerDto(
        id=trigger.id,
        type=trigger.type,
        person_id=trigger.person_id,
        person_name=person_name,
        tag_id=trigger.tag_id,
        tag_name=tag_name,
        phrase=trigger.phrase,
        negate=trigger.negate,
    )


def _build_collection_dto(session: Session, collection: Collection) -> CollectionDto:
    member_ids = _member_asset_ids(session, collection.id)
    return CollectionDto(
        id=collection.id,
        name=collection.name,
        kind=collection.kind,
        match_mode=collection.match_mode,
        member_count=len(member_ids),
        cover_assets=_cover_assets(session, collection),
        description=collection.description,
        cover_asset_id=collection.cover_asset_id,
        settings=TrainingSetSettings(**collection.settings) if collection.settings else None,
    )


def _build_detail_dto(session: Session, collection: Collection) -> CollectionDetailDto:
    base = _build_collection_dto(session, collection)
    triggers = session.query(SmartTrigger).filter_by(collection_id=collection.id).all()
    return CollectionDetailDto(
        **base.model_dump(),
        triggers=[_build_trigger_dto(session, trigger) for trigger in triggers],
        item_order=_item_order(session, collection.id),
    )


def _get_collection_or_404(session: Session, collection_id: int) -> Collection:
    collection = session.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.get("", response_model=list[CollectionDto])
async def list_collections(session: DbSession) -> list[CollectionDto]:
    collections = session.query(Collection).order_by(Collection.name).all()
    return [_build_collection_dto(session, collection) for collection in collections]


@router.post("", response_model=CollectionDetailDto, status_code=201)
async def create_collection(body: CreateCollectionRequest, session: DbSession) -> CollectionDetailDto:
    if body.kind not in _VALID_KINDS:
        raise HTTPException(status_code=422, detail="invalid kind")
    if body.match_mode not in _VALID_MATCH_MODES:
        raise HTTPException(status_code=422, detail="invalid match_mode")
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name must not be empty")

    collection = Collection(name=name, kind=body.kind, match_mode=body.match_mode)
    session.add(collection)
    session.commit()
    session.refresh(collection)
    log.info("Created collection %d (%s, %s)", collection.id, collection.name, collection.kind)
    return _build_detail_dto(session, collection)


@router.get("/{collection_id}", response_model=CollectionDetailDto)
async def get_collection(collection_id: int, session: DbSession) -> CollectionDetailDto:
    collection = _get_collection_or_404(session, collection_id)
    return _build_detail_dto(session, collection)


@router.patch("/{collection_id}", response_model=CollectionDetailDto)
async def update_collection(
    collection_id: int, body: UpdateCollectionRequest, session: DbSession
) -> CollectionDetailDto:
    collection = _get_collection_or_404(session, collection_id)

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="name must not be empty")
        collection.name = name

    if body.match_mode is not None:
        if body.match_mode not in _VALID_MATCH_MODES:
            raise HTTPException(status_code=422, detail="invalid match_mode")
        collection.match_mode = body.match_mode

    became_smart = False
    if body.kind is not None:
        if body.kind not in _VALID_KINDS:
            raise HTTPException(status_code=422, detail="invalid kind")
        was_smart = collection.kind == "smart_album"
        collection.kind = body.kind
        if body.kind != "smart_album" and was_smart:
            # smart turned off: drop auto-materialized rows, keep hand-picked ones
            session.query(CollectionItem).filter_by(
                collection_id=collection_id, source="smart"
            ).delete()
        became_smart = body.kind == "smart_album" and not was_smart

    fields_set = body.model_fields_set
    if "description" in fields_set:
        description = (body.description or "").strip()
        collection.description = description or None
    if "cover_asset_id" in fields_set:
        if body.cover_asset_id is not None and session.get(Asset, body.cover_asset_id) is None:
            raise HTTPException(status_code=422, detail="cover_asset_id: asset not found")
        collection.cover_asset_id = body.cover_asset_id

    if "settings" in fields_set:
        split_ratio = body.settings.split_ratio if body.settings is not None else None
        if split_ratio is not None and not 0.0 < split_ratio <= 1.0:
            raise HTTPException(status_code=422, detail="split_ratio must be in (0.0, 1.0]")
        collection.settings = body.settings.model_dump() if body.settings is not None else None

    session.commit()

    # match-mode change or smart just turned on → membership must be recomputed
    if collection.kind == "smart_album" and (became_smart or body.match_mode is not None):
        await enqueue_reevaluate_collection(collection_id)

    session.refresh(collection)
    return _build_detail_dto(session, collection)


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(collection_id: int, session: DbSession) -> Response:
    collection = _get_collection_or_404(session, collection_id)
    session.query(CollectionItem).filter_by(collection_id=collection_id).delete()
    session.query(SmartTrigger).filter_by(collection_id=collection_id).delete()
    session.delete(collection)
    session.commit()
    return Response(status_code=204)


@router.get("/{collection_id}/triggers", response_model=list[TriggerDto])
async def list_triggers(collection_id: int, session: DbSession) -> list[TriggerDto]:
    _get_collection_or_404(session, collection_id)
    triggers = session.query(SmartTrigger).filter_by(collection_id=collection_id).all()
    return [_build_trigger_dto(session, trigger) for trigger in triggers]


@router.post("/{collection_id}/triggers", response_model=TriggerDto, status_code=201)
async def add_trigger(
    collection_id: int, body: CreateTriggerRequest, session: DbSession
) -> TriggerDto:
    _get_collection_or_404(session, collection_id)
    if body.type not in _VALID_TRIGGER_TYPES:
        raise HTTPException(status_code=422, detail="invalid trigger type")
    if body.type == "tag" and body.tag_id is None:
        raise HTTPException(status_code=422, detail="tag trigger needs tag_id")
    if body.type == "caption" and not (body.phrase or "").strip():
        raise HTTPException(status_code=422, detail="caption trigger needs phrase")
    if body.type == "person" and body.person_id is None:
        raise HTTPException(status_code=422, detail="person trigger needs person_id")

    trigger = SmartTrigger(
        collection_id=collection_id,
        type=body.type,
        person_id=body.person_id,
        tag_id=body.tag_id,
        phrase=(body.phrase or "").strip() or None,
        negate=body.negate,
    )
    session.add(trigger)
    session.commit()
    session.refresh(trigger)

    await enqueue_reevaluate_collection(collection_id)
    return _build_trigger_dto(session, trigger)


@router.patch("/{collection_id}/triggers/{trigger_id}", response_model=TriggerDto)
async def update_trigger(
    collection_id: int, trigger_id: int, body: UpdateTriggerRequest, session: DbSession
) -> TriggerDto:
    trigger = session.get(SmartTrigger, trigger_id)
    if trigger is None or trigger.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Trigger not found")
    trigger.negate = body.negate
    session.commit()
    session.refresh(trigger)

    await enqueue_reevaluate_collection(collection_id)
    return _build_trigger_dto(session, trigger)


@router.delete("/{collection_id}/triggers/{trigger_id}", status_code=204)
async def delete_trigger(collection_id: int, trigger_id: int, session: DbSession) -> Response:
    trigger = session.get(SmartTrigger, trigger_id)
    if trigger is None or trigger.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Trigger not found")
    session.delete(trigger)
    session.commit()

    await enqueue_reevaluate_collection(collection_id)
    return Response(status_code=204)


@router.post("/{collection_id}/reevaluate", response_model=JobStarted, status_code=202)
async def reevaluate_collection(collection_id: int, session: DbSession) -> JobStarted:
    _get_collection_or_404(session, collection_id)
    status = await enqueue_reevaluate_collection(collection_id)
    return JobStarted(job_id=status.id)


@router.post("/{collection_id}/items", status_code=204)
async def add_items(collection_id: int, body: AddItemsRequest, session: DbSession) -> Response:
    """Add hand-picked members (Bulk-Bar „Zu Album"). Manual rows win over smart ones."""
    _get_collection_or_404(session, collection_id)
    for asset_id in body.asset_ids:
        item = (
            session.query(CollectionItem)
            .filter_by(collection_id=collection_id, asset_id=asset_id)
            .first()
        )
        if item is None:
            session.add(CollectionItem(collection_id=collection_id, asset_id=asset_id, source="manual"))
        else:
            item.source = "manual"
    session.commit()
    log.info("Added %d manual item(s) to collection %d", len(body.asset_ids), collection_id)
    return Response(status_code=204)


@router.post("/{collection_id}/export", response_model=JobStarted, status_code=202)
async def export_collection(collection_id: int, body: CollectionExportRequest, session: DbSession) -> JobStarted:
    """Copy all items in the collection to a dated export folder (background job).

    Training sets can additionally request Kohya-style sidecar `.txt` files (tags/caption/
    both — effective caption incl. override) and a deterministic train/val split. Plain
    albums leave `sidecar`/`split_ratio` unset and get the original flat copy behaviour.
    """
    from photofant.jobs.export_job import enqueue_export_collection

    collection = _get_collection_or_404(session, collection_id)
    if body.split_ratio is not None and not 0.0 < body.split_ratio <= 1.0:
        raise HTTPException(status_code=422, detail="split_ratio must be in (0.0, 1.0]")

    split_ratio = body.split_ratio
    if split_ratio is None and collection.settings:
        split_ratio = collection.settings.get("split_ratio")

    status = await enqueue_export_collection(
        collection_id, collection.name, sidecar=body.sidecar, split_ratio=split_ratio, target_dir=body.target_dir
    )
    return JobStarted(job_id=status.id)


@router.delete("/{collection_id}/items/{asset_id}", status_code=204)
async def remove_item(collection_id: int, asset_id: int, session: DbSession) -> Response:
    item = (
        session.query(CollectionItem)
        .filter_by(collection_id=collection_id, asset_id=asset_id)
        .first()
    )
    if item is not None:
        session.delete(item)
        session.commit()
    return Response(status_code=204)


@router.get("/{collection_id}/items", response_model=list[TrainingSetItemDto])
async def list_training_set_items(collection_id: int, session: DbSession) -> list[TrainingSetItemDto]:
    """Full item detail for the training-set editor (caption/tags/quality — the gallery
    grid's `AssetDto` deliberately stays thin, so this is its own read model)."""
    _get_collection_or_404(session, collection_id)
    rows = (
        session.query(Asset, CollectionItem.caption_override)
        .join(CollectionItem, CollectionItem.asset_id == Asset.id)
        .join(AssetInstance, AssetInstance.asset_id == Asset.id)
        .filter(CollectionItem.collection_id == collection_id, AssetInstance.deleted_at.is_(None))
        .distinct()
        .all()
    )
    items: list[TrainingSetItemDto] = []
    for asset, caption_override in rows:
        tag_rows = (
            session.query(Tag.id, Tag.name, AssetTag.kind, AssetTag.score)
            .join(AssetTag, AssetTag.tag_id == Tag.id)
            .filter(AssetTag.asset_id == asset.id, AssetTag.manually_removed.is_(False))
            .all()
        )
        items.append(
            TrainingSetItemDto(
                id=asset.id,
                content_hash=asset.content_hash,
                width=asset.width,
                height=asset.height,
                framing=asset.framing,
                quality=asset.quality_score,
                caption=asset.caption,
                caption_override=caption_override,
                effective_caption=caption_override or asset.caption,
                tags=[TagDto(id=row.id, name=row.name, kind=row.kind, score=row.score) for row in tag_rows],
            )
        )
    return items


@router.patch("/{collection_id}/items/{asset_id}", status_code=204)
async def update_item_caption(
    collection_id: int, asset_id: int, body: UpdateItemCaptionRequest, session: DbSession
) -> Response:
    """Set the training-set-only caption override (Original-Caption der Galerie bleibt unangetastet)."""
    item = (
        session.query(CollectionItem)
        .filter_by(collection_id=collection_id, asset_id=asset_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found in collection")
    item.caption_override = (body.caption_override or "").strip() or None
    session.commit()
    return Response(status_code=204)


@router.get("/{collection_id}/stats", response_model=TrainingSetStatsDto)
async def get_training_set_stats(collection_id: int, session: DbSession) -> TrainingSetStatsDto:
    _get_collection_or_404(session, collection_id)
    stats = compute_training_set_stats(session, collection_id)
    return TrainingSetStatsDto(
        total=stats.total,
        framing=[DistItemDto(value=item.value, count=item.count) for item in stats.framing],
        tag_frequencies=[
            TagFrequencyDto(name=item.name, count=item.count) for item in stats.tag_frequencies
        ],
        quality_histogram=[
            HistogramBucketDto(label=item.label, count=item.count) for item in stats.quality_histogram
        ],
        ar_buckets=[DistItemDto(value=item.value, count=item.count) for item in stats.ar_buckets],
        near_dupe_rate=stats.near_dupe_rate,
    )


@router.post("/{collection_id}/captions", response_model=JobStarted, status_code=202)
async def apply_caption_action_to_set(
    collection_id: int, body: CaptionActionRequest, session: DbSession
) -> JobStarted:
    """Set-wide caption tool (Trigger-Word/Prefix/Suffix/Find-Replace) — queued (Critical Rule 5).

    Writes only `caption_override`; the gallery's original `caption` is never touched.
    """
    from photofant.jobs.captions_job import enqueue_apply_captions

    _get_collection_or_404(session, collection_id)

    if body.action == "trigger_word" and not (body.params.get("word") or "").strip():
        raise HTTPException(status_code=422, detail="trigger_word needs 'word'")
    if body.action in ("prefix", "suffix") and not (body.params.get("text") or "").strip():
        raise HTTPException(status_code=422, detail=f"{body.action} needs 'text'")
    if body.action == "find_replace" and not (body.params.get("find") or ""):
        raise HTTPException(status_code=422, detail="find_replace needs 'find'")

    status = await enqueue_apply_captions(collection_id, body.action, body.params)
    return JobStarted(job_id=status.id)


@router.get("/{collection_id}/duplicates", response_model=list[CollectionDupePairDto])
async def list_collection_duplicates(
    collection_id: int, session: DbSession, threshold: float | None = None
) -> list[CollectionDupePairDto]:
    """Near-dupe pairs (CLIP) among active set members, for the Links-Rechts-Review.

    Computed live, same reasoning as `compute_training_set_stats`: at training-set sizes
    (bis niedrige Hunderte) the O(n²) CLIP pairwise comparison is well under a second, so a
    persisted review queue (like the library-wide `review_item` table) would be
    overengineering here.
    """
    from photofant.settings import load_settings

    _get_collection_or_404(session, collection_id)
    settings = load_settings()
    effective_threshold = (
        threshold if threshold is not None else settings["training_near_dupe_clip_threshold"]
    )
    effective_threshold = max(0.0, min(effective_threshold, _DUPE_MAX_THRESHOLD))

    rows = (
        session.query(Asset.id, Asset.clip_embedding, Asset.content_hash)
        .join(CollectionItem, CollectionItem.asset_id == Asset.id)
        .join(AssetInstance, AssetInstance.asset_id == Asset.id)
        .filter(
            CollectionItem.collection_id == collection_id,
            AssetInstance.deleted_at.is_(None),
            Asset.clip_embedding.is_not(None),
        )
        .distinct()
        .all()
    )
    assets = [(row[0], bytes(row[1]), row[2]) for row in rows]

    pairs: list[CollectionDupePairDto] = []
    if len(assets) >= 2:
        asset_ids = [asset_id for asset_id, _, _ in assets]
        content_hashes = [content_hash for _, _, content_hash in assets]
        vectors = np.stack([np.frombuffer(blob, dtype=np.float32) for _, blob, _ in assets])
        similarities = vectors @ vectors.T
        distances = 1.0 - similarities

        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                distance = float(distances[i, j])
                if distance > effective_threshold:
                    continue
                similarity_pct = round((1.0 - distance) * 100)
                pairs.append(
                    CollectionDupePairDto(
                        asset_a_id=asset_ids[i],
                        asset_b_id=asset_ids[j],
                        asset_a_content_hash=content_hashes[i],
                        asset_b_content_hash=content_hashes[j],
                        clip_distance=distance,
                        similarity_pct=similarity_pct,
                    )
                )
    pairs.sort(key=lambda pair: pair.clip_distance)
    return pairs


@router.post("/{collection_id}/duplicates/resolve", status_code=204)
async def resolve_collection_duplicate(
    collection_id: int, body: ResolveDuplicateRequest, session: DbSession
) -> Response:
    """Discard the losing side of a near-dupe pair into the trash (Papierkorb, P2-Strecke).

    `keep_both` is a client-side dismiss only (not persisted) — same trade-off as the
    live-computed pair list above: reopening the review may resurface a dismissed pair.
    """
    from photofant.media import moves

    _get_collection_or_404(session, collection_id)
    if body.resolution == "keep_both":
        return Response(status_code=204)

    loser_asset_id = body.asset_b_id if body.resolution == "keep_left" else body.asset_a_id
    instances = (
        session.query(AssetInstance)
        .filter(AssetInstance.asset_id == loser_asset_id, AssetInstance.deleted_at.is_(None))
        .all()
    )
    if instances:
        # An asset can have multiple instances (one per detected face/person),
        # so all of them need to move to trash together.
        data_root = get_data_root()
        for instance in instances:
            await moves.soft_delete(session, instance, data_root)
    return Response(status_code=204)


@router.put("/{collection_id}/order", status_code=204)
async def reorder_items(collection_id: int, body: ReorderItemsRequest, session: DbSession) -> Response:
    """Set manual `position` per given order (index in the list = position)."""
    _get_collection_or_404(session, collection_id)
    items = {
        item.asset_id: item
        for item in session.query(CollectionItem).filter_by(collection_id=collection_id).all()
    }
    for position, asset_id in enumerate(body.asset_ids):
        item = items.get(asset_id)
        if item is not None:
            item.position = position
    session.commit()
    return Response(status_code=204)
