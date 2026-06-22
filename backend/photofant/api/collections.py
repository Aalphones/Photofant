"""Collections endpoint — albums & smart albums (Konzept §10.1).

One album type with an optional smart mode: `kind = 'album'` is hand-curated,
`kind = 'smart_album'` is trigger-filled (and may still carry manual members). Toggling
the smart mode flips `kind`; turning it off drops the auto-materialized `source = 'smart'`
rows but keeps the hand-picked ones.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.db.models import (
    Asset,
    AssetInstance,
    Collection,
    CollectionItem,
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
    tag_id: int | None
    tag_name: str | None
    phrase: str | None
    negate: bool


class CoverAssetDto(BaseModel):
    id: int
    content_hash: str


class CollectionDto(BaseModel):
    id: int
    name: str
    kind: str
    match_mode: str
    member_count: int
    cover_assets: list[CoverAssetDto]


class CollectionDetailDto(CollectionDto):
    triggers: list[TriggerDto]


class CreateCollectionRequest(BaseModel):
    name: str
    kind: str = "album"
    match_mode: str = "any"


class UpdateCollectionRequest(BaseModel):
    name: str | None = None
    kind: str | None = None
    match_mode: str | None = None


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


def _cover_assets(session: Session, collection_id: int) -> list[CoverAssetDto]:
    """Up to 4 cover assets (id + content_hash) for album thumbnail display."""
    rows = (
        session.query(CollectionItem.asset_id, Asset.content_hash)
        .join(Asset, Asset.id == CollectionItem.asset_id)
        .join(AssetInstance, AssetInstance.asset_id == CollectionItem.asset_id)
        .filter(CollectionItem.collection_id == collection_id, AssetInstance.deleted_at.is_(None))
        .distinct()
        .limit(4)
        .all()
    )
    return [CoverAssetDto(id=row[0], content_hash=row[1]) for row in rows]


def _build_trigger_dto(session: Session, trigger: SmartTrigger) -> TriggerDto:
    tag_name: str | None = None
    if trigger.type == "tag" and trigger.tag_id is not None:
        tag = session.get(Tag, trigger.tag_id)
        tag_name = tag.name if tag is not None else None
    return TriggerDto(
        id=trigger.id,
        type=trigger.type,
        person_id=trigger.person_id,
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
        cover_assets=_cover_assets(session, collection.id),
    )


def _build_detail_dto(session: Session, collection: Collection) -> CollectionDetailDto:
    base = _build_collection_dto(session, collection)
    triggers = session.query(SmartTrigger).filter_by(collection_id=collection.id).all()
    return CollectionDetailDto(
        **base.model_dump(),
        triggers=[_build_trigger_dto(session, trigger) for trigger in triggers],
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
