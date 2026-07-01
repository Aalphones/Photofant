"""Caption bulk-action job — apply one caption tool to every member of a training set.

POST /api/collections/{id}/captions  →  { action, params }

Runs through the queue so large sets don't block the UI (Critical Rule 5); progress is
reported once per collection (the DB write itself is a single fast pass, not per-image
model inference — unlike tagging/captioning jobs, so a single progress jump is honest
here rather than padding the UI with fake granularity).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from photofant.collections.captions import CaptionAction, apply_caption_action
from photofant.db.models import Asset, AssetInstance, CollectionItem
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


def _apply_to_collection(collection_id: int, action: CaptionAction, params: dict[str, Any]) -> int:
    with SessionLocal() as session:
        rows = (
            session.query(CollectionItem, Asset.caption)
            .join(Asset, Asset.id == CollectionItem.asset_id)
            .join(AssetInstance, AssetInstance.asset_id == CollectionItem.asset_id)
            .filter(CollectionItem.collection_id == collection_id, AssetInstance.deleted_at.is_(None))
            .distinct()
            .all()
        )
        changed = 0
        for item, original_caption in rows:
            base = item.caption_override if item.caption_override is not None else original_caption
            new_value = apply_caption_action(base, action, params)
            if new_value != (item.caption_override or ""):
                item.caption_override = new_value or None
                changed += 1
        session.commit()
    return changed


async def run_apply_captions_job(
    status: JobStatus, collection_id: int, action: CaptionAction, params: dict[str, Any]
) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    changed = await asyncio.to_thread(_apply_to_collection, collection_id, action, params)
    job_queue.update(status, progress=1.0, state=JobState.DONE)
    log.info(
        "Caption action '%s' applied to collection %d (%d item(s) changed)", action, collection_id, changed
    )


async def enqueue_apply_captions(
    collection_id: int, action: CaptionAction, params: dict[str, Any]
) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.CAPTIONS,
        label=f"Caption-Tool „{action}“ auf Trainingsset {collection_id}",
        coro_factory=lambda job_status: run_apply_captions_job(job_status, collection_id, action, params),
    )
