from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select

from photofant.db.cache import THUMBNAIL_SIZES, get_cache_db_path, get_thumbnail, init_cache_db, store_thumbnail
from photofant.db.models import AssetInstance
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.media.thumbnails import generate_thumbnail

log = logging.getLogger(__name__)


def gather_active_asset_ids() -> list[int]:
    """Every asset with an active instance — not soft-deleted, not acknowledged-missing."""
    with SessionLocal() as session:
        rows = session.execute(
            select(AssetInstance.asset_id)
            .where(AssetInstance.deleted_at.is_(None))
            .where(AssetInstance.missing_at.is_(None))
            .distinct()
        ).all()
    return [int(row[0]) for row in rows]


def _missing_sizes(db_path: Path, asset_id: int) -> list[int]:
    return [size for size in THUMBNAIL_SIZES if get_thumbnail(db_path, asset_id, size) is None]


def _process_one(db_path: Path, asset_id: int, source_path: Path, size: int) -> None:
    try:
        data = generate_thumbnail(source_path, size)
        store_thumbnail(db_path, asset_id, size, data)
    except OSError as exc:
        log.warning("Thumbnail generation failed for asset %d size %d: %s", asset_id, size, exc)


async def _thumbnails_for_asset(db_path: Path, asset_id: int) -> None:
    """Fill in whichever sizes are still missing for one asset."""
    from photofant.media.asset_paths import resolve_asset_path

    pending_sizes = _missing_sizes(db_path, asset_id)
    if not pending_sizes:
        return

    source_path = await asyncio.to_thread(resolve_asset_path, asset_id)
    if source_path is None:
        log.warning("Asset %d has no readable file — skipping thumbnails", asset_id)
        return

    for size in pending_sizes:
        await asyncio.to_thread(_process_one, db_path, asset_id, source_path, size)


async def generate_thumbnails(status: JobStatus, db_path: Path, asset_ids: list[int]) -> None:
    """Generate thumbnails (all THUMBNAIL_SIZES) for the given assets.

    Skips sizes that already exist in the cache DB — callers wanting a full
    regeneration must clear the cache first (see the rebuild job). The source
    path is resolved per asset right before reading it, never taken from the
    caller: a long batch outlives plenty of file moves.
    """
    total = len(asset_ids)
    if total == 0:
        return

    for index, asset_id in enumerate(asset_ids):
        await _thumbnails_for_asset(db_path, asset_id)
        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)


async def run_thumbnail_job(status: JobStatus, asset_ids: list[int]) -> None:
    """Generate 256+512 thumbnails for the given assets."""
    db_path = get_cache_db_path()
    init_cache_db(db_path)
    await generate_thumbnails(status, db_path, asset_ids)
    log.info("Thumbnails generated for %d assets", len(asset_ids))


async def enqueue_thumbnails(asset_ids: list[int]) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.THUMBNAIL,
        label=f"Thumbnails: {len(asset_ids)} Bild(er)",
        coro_factory=lambda job_status: run_thumbnail_job(job_status, asset_ids),
    )


async def run_thumbnail_rebuild_job(status: JobStatus) -> None:
    """Additive rebuild: generate missing sizes only, never clears the cache."""
    db_path = get_cache_db_path()
    init_cache_db(db_path)
    asset_ids = gather_active_asset_ids()
    await generate_thumbnails(status, db_path, asset_ids)
    log.info("Thumbnail rebuild (additive) complete for %d assets", len(asset_ids))


async def enqueue_thumbnail_rebuild() -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.THUMBNAIL_REBUILD,
        label="Thumbnails neu generieren",
        coro_factory=lambda job_status: run_thumbnail_rebuild_job(job_status),
    )
