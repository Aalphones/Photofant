"""Re-evaluation job — keeps smart-album membership in sync off the UI thread.

Two flavours, both routed through the single queue worker (Critical Rule 5: the UI
never blocks):
- per asset / asset list: a tag/caption/person change on those assets is re-evaluated
  against every smart album.
- per collection: a trigger or match-mode change re-evaluates that album against all
  assets.
"""
from __future__ import annotations

import asyncio
import logging

from photofant.collections import engine
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


def _reevaluate_assets(asset_ids: list[int]) -> None:
    with SessionLocal() as session:
        for asset_id in asset_ids:
            engine.evaluate_asset(session, asset_id)


def _reevaluate_collection(collection_id: int) -> None:
    with SessionLocal() as session:
        engine.evaluate_collection(session, collection_id)


async def run_reevaluate_assets_job(status: JobStatus, asset_ids: list[int]) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_reevaluate_assets, asset_ids)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def run_reevaluate_collection_job(status: JobStatus, collection_id: int) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_reevaluate_collection, collection_id)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_reevaluate_assets(asset_ids: list[int]) -> JobStatus | None:
    if not asset_ids:
        return None
    return await job_queue.enqueue(
        kind=JobKind.REEVALUATE,
        label=f"Smart-Alben: {len(asset_ids)} Bild(er) neu bewerten",
        coro_factory=lambda job_status: run_reevaluate_assets_job(job_status, asset_ids),
    )


async def enqueue_reevaluate_collection(collection_id: int) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.REEVALUATE,
        label=f"Smart-Album {collection_id}: neu bewerten",
        coro_factory=lambda job_status: run_reevaluate_collection_job(job_status, collection_id),
    )
