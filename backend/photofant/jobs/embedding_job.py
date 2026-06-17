"""Embedding job — runs CLIP inference and persists the image embedding + index row.

One job per asset; controlled by ProcessingLedger.embedding_done (run exactly once).
The canonical embedding lives on `asset.clip_embedding` (float32 BLOB); the searchable
copy goes into the sqlite-vec index (ADR-001).
"""
from __future__ import annotations

import logging

import numpy as np

from photofant.db.models import Asset, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.db.vector_index import upsert_embedding
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


def _run_embedding(asset_id: int, asset_path: str) -> None:
    """Blocking: run CLIP inference + persist the embedding for one asset."""
    from PIL import Image as PILImage

    from photofant.inference.adapters.clip import resolve_clip_embedder

    embedder = resolve_clip_embedder()
    if embedder is None:
        log.info("CLIP not enabled — skipping embedding for asset %d", asset_id)
        return

    image = np.array(PILImage.open(asset_path).convert("RGB"), dtype=np.uint8)
    embedding = embedder.embed(image)

    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            log.warning("Asset %d not found — skipping embedding persist", asset_id)
            return

        asset.clip_embedding = np.ascontiguousarray(embedding, dtype=np.float32).tobytes()
        upsert_embedding(session, asset_id, embedding)

        ledger = session.get(ProcessingLedger, asset.content_hash)
        if ledger is not None:
            ledger.embedding_done = True

        session.commit()

    log.info("Embedded asset %d (%d dims)", asset_id, embedding.shape[0])


async def run_embedding_job(status: JobStatus, asset_id: int, asset_path: str) -> None:
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_embedding, asset_id, asset_path)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_embedding(asset_id: int, asset_path: str) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.EMBEDDING,
        label=f"Embedding: Asset {asset_id}",
        coro_factory=lambda job_status: run_embedding_job(job_status, asset_id, asset_path),
    )
