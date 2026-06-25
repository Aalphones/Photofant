"""Reconcile repair actions — apply one explicit, user-chosen fix per item.

Every function here acts on a *single* discrepancy that the user picked in the
report; there is no auto-repair. Filesystem-touching paths are validated to live
under the data root before anything is moved or deleted, so a crafted report
entry can never make a repair touch a file outside the library.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from photofant.db.models import AssetInstance
from photofant.media import moves

log = logging.getLogger(__name__)


class RepairError(Exception):
    """A repair action could not be applied."""


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def ensure_under_root(path: Path, data_root: Path) -> Path:
    resolved = path.resolve()
    root = data_root.resolve()
    if os.path.commonpath([str(resolved), str(root)]) != str(root):
        raise RepairError(f"Path is outside the data root: {path}")
    return resolved


def _load_instance(session: Session, instance_id: int) -> AssetInstance:
    instance = session.get(AssetInstance, instance_id)
    if instance is None:
        raise RepairError(f"asset_instance {instance_id} not found")
    return instance


async def trash_orphan(session: Session, path: str, data_root: Path) -> None:
    """Move an orphaned file into the trash (it has no DB row to touch)."""
    source = ensure_under_root(Path(path), data_root)
    if not source.exists():
        raise RepairError(f"Orphaned file no longer exists: {path}")
    await moves.trash_orphan_file(source, data_root)


def mark_missing(session: Session, instance_id: int) -> None:
    """Acknowledge a missing file: stamp `missing_at` so later scans skip it."""
    instance = _load_instance(session, instance_id)
    instance.missing_at = _now_utc()
    session.commit()


async def purge_missing(session: Session, instance_id: int, cache_db_path: Path) -> None:
    """Drop the DB row for a missing instance (the file is already gone)."""
    instance = _load_instance(session, instance_id)
    await moves.purge(session, instance, cache_db_path)


async def purge_orphaned_face(session: Session, face_id: int, cache_db_path: Path) -> None:
    """Remove a Face record whose parent Asset is gone: crop file, thumbnail, embedding, row."""
    await moves.purge_face(session, face_id, cache_db_path)


def fix_drift(session: Session, instance_id: int, found_path: str, data_root: Path) -> None:
    """Point the instance at the rediscovered file and clear any missing marker."""
    target = ensure_under_root(Path(found_path), data_root)
    if not target.exists():
        raise RepairError(f"Drift target no longer exists: {found_path}")
    instance = _load_instance(session, instance_id)
    instance.path = str(target)
    instance.missing_at = None
    session.commit()
