from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy import select

from photofant.db.cache import clear_cache, get_cache_db_path, init_cache_db
from photofant.db.models import AssetInstance
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.jobs.thumbnail_job import generate_thumbnails

log = logging.getLogger(__name__)

RebuildTarget = Literal["thumbnails"]

_TARGET_LABELS: dict[str, str] = {
    "thumbnails": "Thumbnails neu aufbauen",
}


def _gather_active_items() -> list[tuple[int, str]]:
    """(asset_id, path) for every active instance — not soft-deleted, not acknowledged-missing."""
    with SessionLocal() as session:
        rows = session.execute(
            select(AssetInstance.asset_id, AssetInstance.path)
            .where(AssetInstance.deleted_at.is_(None))
            .where(AssetInstance.missing_at.is_(None))
        ).all()
    return [(row[0], row[1]) for row in rows]


async def _rebuild_thumbnails(status: JobStatus) -> None:
    """Drop the whole thumbnail cache and regenerate it from the source images.

    Safe to interrupt: thumbnails are pure cache (originals are never touched)
    and any not yet regenerated are recreated lazily on first request.
    """
    db_path = get_cache_db_path()
    init_cache_db(db_path)
    clear_cache(db_path)

    items = _gather_active_items()
    await generate_thumbnails(status, db_path, items)
    log.info("Thumbnail cache rebuilt for %d instances", len(items))


async def run_rebuild_job(status: JobStatus, target: RebuildTarget) -> None:
    if target == "thumbnails":
        await _rebuild_thumbnails(status)
    else:  # pragma: no cover - guarded by the API Literal
        raise ValueError(f"unknown rebuild target '{target}'")

    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_rebuild(target: RebuildTarget) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.REBUILD,
        label=_TARGET_LABELS.get(target, f"Rebuild: {target}"),
        coro_factory=lambda job_status: run_rebuild_job(job_status, target),
    )
