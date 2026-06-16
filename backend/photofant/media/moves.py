"""Crash-safe file moves coupled with their DB path update.

This is *the* reusable move helper. Favourites toggle the photos/ ↔ favourites/
subfolder, soft-delete relocates into .photofant/trash/ (mirroring the data-root
tree so a restore can reconstruct the original path), and purge wipes file +
thumbnails + DB rows.

Ordering is always **filesystem first, then a single DB commit**. A crash in
between leaves the file durably in its new spot while the DB still points at the
old path — a forward-recoverable drift that the P3 reconciliation detects and
that the helpers here heal on the next run (source gone + dest present → adopt
dest, sync DB only).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from photofant.db.cache import delete_thumbnails, init_cache_db
from photofant.db.models import Asset, AssetInstance, ProcessingLedger

log = logging.getLogger(__name__)

_TRASH_SUBDIR = Path(".photofant") / "trash"
_PHOTOS_SUBFOLDER = "photos"
_FAVOURITES_SUBFOLDER = "favourites"


class MoveError(Exception):
    """A tracked file move could not be completed."""


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _resolve_collision(dest: Path) -> Path:
    """Return dest, or a numerically suffixed sibling if dest is already taken."""
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    counter = 1
    candidate = dest.with_name(f"{stem}_{counter}{suffix}")
    while candidate.exists():
        counter += 1
        candidate = dest.with_name(f"{stem}_{counter}{suffix}")
    return candidate


def _perform_move(source: Path, dest: Path) -> Path:
    """Move source → dest on disk and return the final path. Restartable.

    Cases handled, in order:
    - source already *is* dest → no-op if the file is there, else the recorded
      file is lost (MoveError).
    - source gone but dest present → a prior move was interrupted before the DB
      commit; adopt dest (DB-only recovery).
    - source present, dest free → plain move.
    - source present, dest taken by a *different* file → suffix the destination
      (collision) and move.
    - source and dest both gone → the file is lost (MoveError).
    """
    if source.resolve() == dest.resolve():
        if dest.exists():
            return dest
        raise MoveError(f"File missing at its recorded path: {source}")

    if not source.exists():
        if dest.exists():
            log.warning(
                "Source %s missing but %s present — adopting it (interrupted prior move)",
                source,
                dest,
            )
            return dest
        raise MoveError(f"Source file missing and no destination present: {source}")

    final = _resolve_collision(dest)
    final.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(source), str(final))
    except OSError as exc:
        raise MoveError(f"Failed to move {source} → {final}: {exc}") from exc
    return final


async def set_favourite(session: Session, instance: AssetInstance, value: bool) -> AssetInstance:
    """Move the file between photos/ and favourites/, then flip the flag — atomically.

    The favourite boolean mirrors the physical location, so both the path and the
    flag are written in the same commit; they can never disagree after a crash.
    """
    source = Path(instance.path)
    person_dir = source.parent.parent  # .../_unknown
    target_subfolder = _FAVOURITES_SUBFOLDER if value else _PHOTOS_SUBFOLDER
    dest = person_dir / target_subfolder / source.name

    final = await asyncio.to_thread(_perform_move, source, dest)

    instance.path = str(final.resolve())
    instance.favourite = value
    session.commit()
    return instance


async def soft_delete(session: Session, instance: AssetInstance, data_root: Path) -> AssetInstance:
    """Relocate the file into .photofant/trash/ (mirroring the tree) and mark deleted."""
    source = Path(instance.path)
    root = data_root.resolve()
    trash_root = root / _TRASH_SUBDIR

    try:
        relative = source.resolve().relative_to(root)
    except ValueError:
        # File lives outside the data root (shouldn't happen) — fall back to the bare name.
        relative = Path(source.name)
    dest = trash_root / relative

    final = await asyncio.to_thread(_perform_move, source, dest)

    instance.path = str(final.resolve())
    instance.deleted_at = _now_utc()
    session.commit()
    return instance


async def restore(session: Session, instance: AssetInstance, data_root: Path) -> AssetInstance:
    """Move the file back out of the trash to its mirrored original path and clear the flag."""
    source = Path(instance.path)
    root = data_root.resolve()
    trash_root = (root / _TRASH_SUBDIR).resolve()

    try:
        relative = source.resolve().relative_to(trash_root)
    except ValueError as exc:
        raise MoveError(f"Instance {instance.id} path {source} is not under the trash; cannot restore") from exc
    dest = root / relative

    final = await asyncio.to_thread(_perform_move, source, dest)

    instance.path = str(final.resolve())
    instance.deleted_at = None
    session.commit()
    return instance


def _delete_file_and_thumbnails(file_path: Path, cache_db_path: Path, asset_id: int) -> None:
    with contextlib.suppress(FileNotFoundError):
        file_path.unlink()
    init_cache_db(cache_db_path)
    delete_thumbnails(cache_db_path, asset_id)


async def purge(session: Session, instance: AssetInstance, cache_db_path: Path) -> None:
    """Permanently remove the file, its thumbnails, and the DB rows.

    The asset + ledger rows are dropped only once their last instance is gone
    (Stage 1 has exactly one instance per asset; the count keeps P7 honest).
    """
    source = Path(instance.path)
    asset_id = instance.asset_id

    await asyncio.to_thread(_delete_file_and_thumbnails, source, cache_db_path, asset_id)

    session.delete(instance)
    session.flush()

    remaining: int = (
        session.scalar(
            select(func.count()).select_from(AssetInstance).where(AssetInstance.asset_id == asset_id)
        )
        or 0
    )
    if remaining == 0:
        asset = session.get(Asset, asset_id)
        if asset is not None:
            ledger = session.get(ProcessingLedger, asset.content_hash)
            if ledger is not None:
                session.delete(ledger)
            session.delete(asset)

    session.commit()
