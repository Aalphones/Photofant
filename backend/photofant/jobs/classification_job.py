"""Classification job — computes + persists asset_classification rows for one asset.

One job per asset; triggered automatically once TAGGING and EMBEDDING have both
completed (via `jobs/classification_pipeline.py`), and by the rerun endpoint's
"categories" step. Controlled by `ProcessingLedger.classified` — idempotent,
replaces the asset's existing rows atomically on each run so a rerun's
recomputed labels never mix with stale ones.
"""
from __future__ import annotations

import logging

from photofant.classification.engine import classify_asset
from photofant.db.models import Asset, AssetClassification, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


def _run_classification(asset_id: int) -> None:
    """Blocking: classify one asset and persist the result (replaces old rows). No image I/O."""
    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            log.warning("Asset %d not found — skipping classification persist", asset_id)
            return

        results = classify_asset(session, asset_id)

        session.query(AssetClassification).filter(
            AssetClassification.asset_id == asset_id
        ).delete(synchronize_session=False)

        for result in results:
            session.add(AssetClassification(
                asset_id=asset_id,
                label_id=result.label_id,
                category_id=result.category_id,
                confidence=result.confidence,
                source=result.source,
            ))

        ledger = session.get(ProcessingLedger, asset.content_hash)
        if ledger is not None:
            ledger.classified = True

        session.commit()

    log.info("Classified asset %d: %d label(s)", asset_id, len(results))


async def run_classification_job(status: JobStatus, asset_id: int) -> None:
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_classification, asset_id)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_classification(asset_id: int) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.CLASSIFICATION,
        label=f"Klassifizierung: Asset {asset_id}",
        coro_factory=lambda job_status: run_classification_job(job_status, asset_id),
    )


async def enqueue_classification_batch(asset_ids: list[int]) -> list[JobStatus]:
    """Batch-enqueue helper for the retro run (explicit selection or "all")."""
    return [await enqueue_classification(asset_id) for asset_id in asset_ids]
