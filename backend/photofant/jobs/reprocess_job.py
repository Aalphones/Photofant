"""Catch-up run — find assets whose processing never finished and requeue it.

A job that dies takes its step with it: the ledger flag stays False, nothing
retries, and the photo sits in the library without tags, caption or faces
forever. Historically the usual killer was a stale file path (fixed by resolving
paths at run time, see media/asset_paths.py), but the gap is structural — a
crashed model, a full disk or a mid-import restart leave the same hole.

This run closes it. It reads the ledger, works out per asset which steps are
still missing, and enqueues *only those* through the regular pipeline. Steps
that already succeeded are not repeated.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from photofant.db.models import Asset, AssetInstance, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.jobs.import_job import PipelineSteps, steps_from_settings
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


def _pending_steps(ledger: ProcessingLedger | None, allowed: PipelineSteps) -> PipelineSteps:
    """The steps that are enabled in settings *and* not yet marked done.

    A missing ledger row means nothing ran at all — everything is pending.
    """
    if ledger is None:
        return allowed

    return PipelineSteps(
        heuristics=allowed.heuristics and not ledger.heuristics_done,
        tags=allowed.tags and not ledger.tags_done,
        caption=allowed.caption and not ledger.caption_done,
        embedding=allowed.embedding and not ledger.embedding_done,
        faces=allowed.faces and not ledger.faces_done,
        classification=allowed.classification and not ledger.classified,
    )


def _has_pending_work(steps: PipelineSteps) -> bool:
    return any(
        (steps.heuristics, steps.tags, steps.caption, steps.embedding, steps.faces, steps.classification)
    )


def collect_incomplete_assets() -> list[tuple[int, PipelineSteps]]:
    """(asset_id, missing steps) for every active asset with unfinished processing."""
    allowed = steps_from_settings()

    with SessionLocal() as session:
        rows = session.execute(
            select(Asset.id, ProcessingLedger)
            .join(AssetInstance, AssetInstance.asset_id == Asset.id)
            .outerjoin(ProcessingLedger, ProcessingLedger.content_hash == Asset.content_hash)
            .where(AssetInstance.deleted_at.is_(None))
            .where(AssetInstance.missing_at.is_(None))
            .distinct()
        ).all()

        pending: list[tuple[int, PipelineSteps]] = []
        for asset_id_raw, ledger in rows:
            steps = _pending_steps(ledger, allowed)
            if _has_pending_work(steps):
                pending.append((int(asset_id_raw), steps))

    return pending


def count_incomplete_assets() -> int:
    """How many active assets still have unfinished processing steps."""
    return len(collect_incomplete_assets())


async def run_reprocess_job(status: JobStatus) -> None:
    from photofant.jobs.import_job import enqueue_pipeline_steps

    job_queue.update(status, progress=0.0, state=JobState.RUNNING)

    pending = collect_incomplete_assets()
    total = len(pending)
    if total == 0:
        log.info("Catch-up run: nothing to reprocess")
        return

    for index, (asset_id, steps) in enumerate(pending):
        await enqueue_pipeline_steps(asset_id, steps)
        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)

    log.info("Catch-up run: requeued processing for %d asset(s)", total)


async def enqueue_reprocess() -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.REPROCESS,
        label="Unfertige Bilder nachverarbeiten",
        coro_factory=lambda job_status: run_reprocess_job(job_status),
    )
