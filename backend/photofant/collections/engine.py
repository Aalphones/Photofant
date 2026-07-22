"""Smart-album evaluation engine (Konzept §10.1).

A smart album (`collection.kind = 'smart_album'`) is auto-filled by its triggers.
Membership is materialized in `collection_item` with `source = 'smart'`, kept separate
from hand-picked rows (`source = 'manual'`). Manual rows are never touched here — a
manual member survives even if it no longer matches the triggers, and a smart match on an
asset that is already a manual member leaves the row as `manual` (manual wins).

Trigger semantics mirror the prototype (`docs/design/js/data.js` matchTriggers/evalTrigger):
- Positive (non-negated) triggers combine via `match_mode`: `all` → AND, `any` → OR.
- Negated triggers exclude: any negated match removes the asset.
- No positive trigger → empty smart membership.

Trigger types:
- `tag`     — asset carries the trigger's tag (aliases resolved, `manually_removed` excluded).
- `caption` — asset caption contains the phrase (case-insensitive substring).
- `person`  — asset has an instance for the trigger's person (P7).
"""
from __future__ import annotations

import logging

from sqlalchemy import or_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from photofant.db.models import (
    Asset,
    AssetInstance,
    AssetTag,
    Collection,
    CollectionItem,
    SmartTrigger,
    Tag,
)

log = logging.getLogger(__name__)


def _active_asset_ids(session: Session) -> set[int]:
    """Asset ids with at least one non-deleted instance."""
    rows = (
        session.query(Asset.id)
        .join(AssetInstance, AssetInstance.asset_id == Asset.id)
        .filter(AssetInstance.deleted_at.is_(None))
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def _trigger_match_ids(session: Session, trigger: SmartTrigger, active_ids: set[int]) -> set[int]:
    """Asset ids matching a single trigger (negate ignored), restricted to active assets."""
    if trigger.type == "tag":
        if trigger.tag_id is None:
            return set()
        alias_ids = [row[0] for row in session.query(Tag.id).filter(Tag.alias_of == trigger.tag_id).all()]
        tag_clause = (
            or_(AssetTag.tag_id == trigger.tag_id, AssetTag.tag_id.in_(alias_ids))
            if alias_ids
            else AssetTag.tag_id == trigger.tag_id
        )
        rows = (
            session.query(AssetTag.asset_id)
            .filter(AssetTag.manually_removed.is_(False), tag_clause)
            .all()
        )
        return {row[0] for row in rows} & active_ids

    if trigger.type == "caption":
        phrase = (trigger.phrase or "").strip()
        if not phrase:
            return set()
        rows = session.query(Asset.id).filter(Asset.caption.ilike(f"%{phrase}%")).all()
        return {row[0] for row in rows} & active_ids

    if trigger.type == "person" and trigger.person_id is not None:
        rows = (
            session.query(AssetInstance.asset_id)
            .filter(
                AssetInstance.person_id == trigger.person_id,
                AssetInstance.deleted_at.is_(None),
            )
            .all()
        )
        return {row[0] for row in rows} & active_ids

    return set()


def compute_smart_members(session: Session, collection: Collection) -> set[int]:
    """Set of asset ids that match a smart album's triggers right now."""
    triggers = session.query(SmartTrigger).filter_by(collection_id=collection.id).all()
    positive = [trigger for trigger in triggers if not trigger.negate]
    negative = [trigger for trigger in triggers if trigger.negate]
    if not positive:
        return set()

    active_ids = _active_asset_ids(session)
    positive_sets = [_trigger_match_ids(session, trigger, active_ids) for trigger in positive]

    if collection.match_mode == "all":
        members = set.intersection(*positive_sets)
    else:
        members = set().union(*positive_sets)

    for trigger in negative:
        members -= _trigger_match_ids(session, trigger, active_ids)

    return members


def _insert_smart_member(session: Session, collection_id: int, asset_id: int) -> None:
    """Idempotent insert — concurrent worker pools (tagging/captioning/reevaluate) can
    race to add the same (collection_id, asset_id) row. `ON CONFLICT DO NOTHING` makes
    the loser a no-op instead of an IntegrityError."""
    stmt = (
        sqlite_insert(CollectionItem)
        .values(collection_id=collection_id, asset_id=asset_id, source="smart")
        .on_conflict_do_nothing(index_elements=["collection_id", "asset_id"])
    )
    session.execute(stmt)


def evaluate_collection(session: Session, collection_id: int) -> None:
    """Re-materialize the smart membership of one album (trigger change / manual re-eval)."""
    collection = session.get(Collection, collection_id)
    if collection is None or collection.kind != "smart_album":
        return

    desired = compute_smart_members(session, collection)
    existing = session.query(CollectionItem).filter_by(collection_id=collection_id).all()
    existing_asset_ids = {item.asset_id for item in existing}

    for asset_id in desired:
        if asset_id not in existing_asset_ids:
            _insert_smart_member(session, collection_id, asset_id)

    for item in existing:
        if item.source == "smart" and item.asset_id not in desired:
            session.delete(item)

    session.commit()
    log.info("Re-evaluated smart album %d: %d member(s)", collection_id, len(desired))


def evaluate_asset(session: Session, asset_id: int) -> None:
    """Re-evaluate one asset against every smart album (tag/caption/person change)."""
    smart_collections = session.query(Collection).filter_by(kind="smart_album").all()
    for collection in smart_collections:
        matches = asset_id in compute_smart_members(session, collection)
        item = (
            session.query(CollectionItem)
            .filter_by(collection_id=collection.id, asset_id=asset_id)
            .first()
        )
        if matches and item is None:
            _insert_smart_member(session, collection.id, asset_id)
        elif not matches and item is not None and item.source == "smart":
            session.delete(item)

    session.commit()
