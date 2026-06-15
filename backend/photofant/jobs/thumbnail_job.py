from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from photofant.db.cache import THUMBNAIL_SIZES, get_cache_db_path, get_thumbnail, init_cache_db, store_thumbnail
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.media.thumbnails import generate_thumbnail

log = logging.getLogger(__name__)


def _process_one(db_path: Path, asset_id: int, source_path: Path, size: int) -> None:
    existing = get_thumbnail(db_path, asset_id, size)
    if existing is not None:
        return
    try:
        data = generate_thumbnail(source_path, size)
        store_thumbnail(db_path, asset_id, size, data)
    except OSError as exc:
        log.warning("Thumbnail generation failed for asset %d size %d: %s", asset_id, size, exc)


async def run_thumbnail_job(status: JobStatus, items: list[tuple[int, str]]) -> None:
    """Generate 256+512 thumbnails for a list of (asset_id, source_path) pairs."""
    db_path = get_cache_db_path()
    init_cache_db(db_path)

    total = len(items) * len(THUMBNAIL_SIZES)
    done = 0

    for asset_id, source_path_str in items:
        source_path = Path(source_path_str)
        for size in THUMBNAIL_SIZES:
            await asyncio.to_thread(_process_one, db_path, asset_id, source_path, size)
            done += 1
            job_queue.update(status, progress=done / total, state=JobState.RUNNING)

    log.info("Thumbnails generated for %d assets", len(items))


async def enqueue_thumbnails(items: list[tuple[int, str]]) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.THUMBNAIL,
        label=f"Thumbnails: {len(items)} Bild(er)",
        coro_factory=lambda job_status: run_thumbnail_job(job_status, items),
    )
