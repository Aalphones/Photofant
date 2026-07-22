"""Resolve an asset's *current* file path, at the moment a job actually needs it.

A job must never carry a path across the queue. Between enqueueing and running,
the file can move: face matching materializes a person assignment, the favourite
toggle swaps photos/ ↔ favourites/, merge/split/delete-person relocate whole
folders. The path a job was handed at import time is a snapshot, and a snapshot
of a moving target is wrong more often than anyone expects.

A stale path used to kill the job with FileNotFoundError. Since a failed job is
never retried, the asset then stayed without tags, caption or faces forever —
silently. So everything that opens an asset file goes through here instead, and
resolves against the DB (which the move helpers keep in sync in the same commit).
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import AssetInstance
from photofant.db.session import SessionLocal

log = logging.getLogger(__name__)


def resolve_asset_path_in(session: Session, asset_id: int) -> Path | None:
    """Current on-disk path of an asset, or None if no instance file is left.

    An asset can have several instances (one per person). Any of them is a valid
    source for inference — they are copies of the same content hash — so the
    first one that actually exists on disk wins. Instances the user soft-deleted
    or that reconcile flagged as missing are skipped.
    """
    rows = session.execute(
        select(AssetInstance.path)
        .where(AssetInstance.asset_id == asset_id)
        .where(AssetInstance.deleted_at.is_(None))
        .where(AssetInstance.missing_at.is_(None))
        .order_by(AssetInstance.id.asc())
    ).all()

    for row in rows:
        candidate = Path(str(row[0]))
        if candidate.exists():
            return candidate

    if rows:
        log.warning(
            "Asset %d: %d instance path(s) recorded, none present on disk (first: %s)",
            asset_id,
            len(rows),
            rows[0][0],
        )
    return None


def resolve_asset_path(asset_id: int) -> Path | None:
    """Session-opening convenience wrapper around `resolve_asset_path_in`."""
    with SessionLocal() as session:
        return resolve_asset_path_in(session, asset_id)
