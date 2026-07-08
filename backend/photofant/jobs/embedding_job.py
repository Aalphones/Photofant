"""Embedding job — runs the active image embedder and persists the embedding + index row.

One job per asset; controlled by ProcessingLedger.embedding_done (run exactly once).
The embedder is resolved by capability (ADR-022), so this job names no model. The
canonical embedding lives on `asset.clip_embedding` (float32 BLOB — the column name
stays for continuity); the searchable copy goes into the sqlite-vec index (ADR-001).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

import numpy as np
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from photofant.db.models import Asset, ProcessingLedger, ReviewItem
from photofant.db.session import SessionLocal
from photofant.db.vector_index import search, upsert_dino_embedding, upsert_embedding
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _check_for_dupes(session: Session, asset_id: int, embedding: np.ndarray) -> None:
    """Post-embedding dupe check via sqlite-vec (P33: runs after the embedding job, not at import time).

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


def _embed_asset(asset_id: int, asset_path: str, *, semantic: bool, dino: bool) -> None:
    """Blocking: run the requested image embedders + persist them for one asset.

    `semantic` = the SigLIP2 (role ``semantic_search``) path: canonical
    ``clip_embedding`` + ``vec_asset_embedding`` + ``embedding_done``, followed by
    the post-embedding dupe check and the classification signal (the primary
    pipeline still advances even when no semantic embedder is enabled).
    `dino` = the DINOv2 (role ``visual_rerank``, P37) path: ``dino_embedding`` +
    ``vec_asset_dino`` + ``dino_embedding_done``.

    The two spaces are independent — a requested role with no enabled model is
    skipped cleanly (its flag stays False), never a crash. The source image is
    opened once and fed to both adapters (each does its own preprocessing).
    """
    from PIL import Image as PILImage

    from photofant.inference.image_embedder import resolve_image_embedder
    from photofant.jobs.classification_pipeline import classification_pipeline

    semantic_embedder = resolve_image_embedder() if semantic else None
    dino_embedder = resolve_image_embedder(role="visual_rerank") if dino else None

    if semantic_embedder is None and dino_embedder is None:
        if semantic:
            # Primary pipeline must advance even without a semantic embedder.
            log.info("No image embedder enabled — skipping embedding for asset %d", asset_id)
            classification_pipeline.signal(asset_id)
        else:
            log.info("No DINOv2 embedder enabled — skipping visual-rerank embedding for asset %d", asset_id)
        return

    image = np.array(PILImage.open(asset_path).convert("RGB"), dtype=np.uint8)

    semantic_embedding: np.ndarray | None = None
    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            log.warning("Asset %d not found — skipping embedding persist", asset_id)
            return

        ledger = session.get(ProcessingLedger, asset.content_hash)

        if semantic_embedder is not None:
            semantic_embedding = semantic_embedder.embed(image)
            asset.clip_embedding = np.ascontiguousarray(semantic_embedding, dtype=np.float32).tobytes()
            upsert_embedding(session, asset_id, semantic_embedding)
            if ledger is not None:
                ledger.embedding_done = True

        if dino_embedder is not None:
            dino_embedding = dino_embedder.embed(image)
            asset.dino_embedding = np.ascontiguousarray(dino_embedding, dtype=np.float32).tobytes()
            upsert_dino_embedding(session, asset_id, dino_embedding)
            if ledger is not None:
                ledger.dino_embedding_done = True
            log.info("Embedded asset %d (DINOv2 %d dims)", asset_id, dino_embedding.shape[0])

        session.commit()

        if semantic_embedding is not None:
            _check_for_dupes(session, asset_id, semantic_embedding)

    if semantic_embedding is not None:
        log.info("Embedded asset %d (SigLIP2 %d dims)", asset_id, semantic_embedding.shape[0])

    if semantic:
        classification_pipeline.signal(asset_id)


def _run_embedding(asset_id: int, asset_path: str) -> None:
    """Blocking: embed both active image models (SigLIP2 + DINOv2) for one asset."""
    _embed_asset(asset_id, asset_path, semantic=True, dino=True)


def _run_dino_embedding(asset_id: int, asset_path: str) -> None:
    """Blocking: (re)embed only the DINOv2 visual-rerank space for one asset.

    Lets an existing library gain the DINOv2 embedding on a rerun without
    recomputing SigLIP2 (rerun step ``dino_embedding``).
    """
    _embed_asset(asset_id, asset_path, semantic=False, dino=True)


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
