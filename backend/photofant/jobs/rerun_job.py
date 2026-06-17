"""Rerun job — bulk reprocessing of classification steps for existing assets.

Resets the selected ProcessingLedger flags for each target asset, then
re-runs the corresponding steps sequentially. A single batch job provides
clean progress reporting; the Ledger guarantees idempotent re-entry if the
job is interrupted.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from sqlalchemy import select

from photofant.db.models import Asset, AssetInstance, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)

ClassifyStep = Literal["tags", "caption", "embedding", "heuristics"]

_STEP_FLAGS: dict[str, str] = {
    "tags": "tags_done",
    "caption": "caption_done",
    "embedding": "embedding_done",
    "heuristics": "heuristics_done",
}


def _resolve_assets(
    asset_ids: list[int] | Literal["all"],
) -> list[tuple[int, str, str]]:
    """Return list of (asset_id, path, content_hash) for non-deleted active assets."""
    with SessionLocal() as session:
        query = (
            select(Asset.id, AssetInstance.path, Asset.content_hash)
            .join(AssetInstance, AssetInstance.asset_id == Asset.id)
            .where(AssetInstance.deleted_at.is_(None))
            .where(AssetInstance.missing_at.is_(None))
        )
        if asset_ids != "all":
            query = query.where(Asset.id.in_(asset_ids))
        rows = session.execute(query).all()
    return [(int(row[0]), str(row[1]), str(row[2])) for row in rows]


def _reset_ledger_flags(content_hash: str, steps: list[ClassifyStep]) -> None:
    with SessionLocal() as session:
        ledger = session.get(ProcessingLedger, content_hash)
        if ledger is None:
            return
        for step in steps:
            flag_name = _STEP_FLAGS.get(step)
            if flag_name is not None:
                setattr(ledger, flag_name, False)
        session.commit()


async def run_rerun_job(
    status: JobStatus,
    asset_ids: list[int] | Literal["all"],
    steps: list[ClassifyStep],
    caption_preset_id: int | None,
) -> None:
    from photofant.jobs.caption_job import _run_caption_with_preset
    from photofant.jobs.embedding_job import _run_embedding
    from photofant.jobs.heuristics_job import _run_heuristics
    from photofant.jobs.tagging_job import _run_tagging

    assets = await asyncio.to_thread(_resolve_assets, asset_ids)
    total = max(len(assets), 1)

    job_queue.update(status, progress=0.0, state=JobState.RUNNING)

    for index, (asset_id, asset_path, content_hash) in enumerate(assets):
        await asyncio.to_thread(_reset_ledger_flags, content_hash, steps)

        if "heuristics" in steps:
            await asyncio.to_thread(_run_heuristics, asset_id, asset_path)
        if "tags" in steps:
            await asyncio.to_thread(_run_tagging, asset_id, asset_path)
        if "caption" in steps:
            await asyncio.to_thread(_run_caption_with_preset, asset_id, asset_path, caption_preset_id)
        if "embedding" in steps:
            await asyncio.to_thread(_run_embedding, asset_id, asset_path)

        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)

    log.info("Rerun done: %d asset(s), steps=%s", len(assets), steps)


async def enqueue_rerun(
    asset_ids: list[int] | Literal["all"],
    steps: list[ClassifyStep],
    caption_preset_id: int | None,
) -> JobStatus:
    count = "alle" if asset_ids == "all" else str(len(asset_ids))
    steps_label = ", ".join(steps)
    return await job_queue.enqueue(
        kind=JobKind.RERUN,
        label=f"Rerun {count} Bild(er): {steps_label}",
        coro_factory=lambda job_status: run_rerun_job(job_status, asset_ids, steps, caption_preset_id),
    )
