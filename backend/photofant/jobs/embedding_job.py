"""Embedding job — runs CLIP inference and persists the image embedding + index row.

One job per asset; controlled by ProcessingLedger.embedding_done (run exactly once).
The canonical embedding lives on `asset.clip_embedding` (float32 BLOB); the searchable
copy goes into the sqlite-vec index (ADR-001).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

import numpy as np
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from photofant.db.models import Asset, ProcessingLedger, ReviewItem
from photofant.db.session import SessionLocal
from photofant.db.vector_index import search, upsert_embedding
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _check_for_dupes(session: Session, asset_id: int, embedding: np.ndarray) -> None:
    """Post-embedding dupe check via sqlite-vec (replaces the former pHash import-time check).

    Own try/except + own commit — a failure here must not roll back the embedding
    result that was already committed by the caller.
    """
    from photofant.settings import load_settings

    settings = load_settings()
    if not settings["dupe_clip_enabled"]:
        return

    clip_threshold: float = settings["dupe_clip_threshold"]
    similarity_floor = 1.0 - clip_threshold

    try:
        hits = search(session, embedding, limit=settings["dupe_search_limit"])
        found = False
        for other_id, similarity in hits:
            if other_id == asset_id or similarity < similarity_floor:
                continue
            asset_a_id, asset_b_id = min(asset_id, other_id), max(asset_id, other_id)
            stmt = sqlite_insert(ReviewItem).values(
                type="dupe_candidate",
                asset_a_id=asset_a_id,
                asset_b_id=asset_b_id,
                clip_distance=1.0 - similarity,
                created_at=_now_utc(),
            ).on_conflict_do_nothing()
            session.execute(stmt)
            found = True
        if found:
            session.commit()
    except Exception:
        log.exception("Post-embedding dupe-check failed for asset %d — continuing", asset_id)
        session.rollback()


def _run_embedding(asset_id: int, asset_path: str) -> None:
    """Blocking: run CLIP inference + persist the embedding for one asset."""
    from PIL import Image as PILImage

    from photofant.inference.adapters.clip import resolve_clip_embedder
    from photofant.jobs.classification_pipeline import classification_pipeline

    embedder = resolve_clip_embedder()
    if embedder is None:
        log.info("CLIP not enabled — skipping embedding for asset %d", asset_id)
        classification_pipeline.signal(asset_id)
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

        _check_for_dupes(session, asset_id, embedding)

    log.info("Embedded asset %d (%d dims)", asset_id, embedding.shape[0])
    classification_pipeline.signal(asset_id)


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
