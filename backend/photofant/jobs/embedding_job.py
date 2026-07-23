"""Embedding job — runs the active image embedder and persists the embedding + index row.

One job per asset; controlled by ProcessingLedger.embedding_done (run exactly once).
The embedder is resolved by capability (ADR-022), so this job names no model. The
canonical embedding is persisted through the embeddings access layer (`db/embeddings.py`);
the searchable copy goes into the sqlite-vec index (ADR-001).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

import numpy as np
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from photofant.db import embeddings
from photofant.db.models import Asset, ProcessingLedger, ReviewItem
from photofant.db.session import SessionLocal
from photofant.db.vector_index import search_dino, upsert_dino_embedding, upsert_embedding
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _check_for_dupes(session: Session, asset_id: int, dino_embedding: np.ndarray) -> None:
    """Post-embedding dupe check via sqlite-vec (P33; on DINOv2 since P37 Phase 4).

    Duplicate detection runs on the DINOv2 visual-rerank space now — visual
    appearance, not semantic content, is what defines a duplicate (ADR-024).
    `dupe_clip_threshold`/SigLIP2 stay inert (rollback). Own try/except + own
    commit — a failure here must not roll back the embedding result that was
    already committed by the caller.
    """
    from photofant.settings import load_settings

    settings = load_settings()
    if not settings["dupe_clip_enabled"]:
        return

    dino_threshold: float = settings["dupe_dino_threshold"]
    similarity_floor = 1.0 - dino_threshold

    try:
        hits = search_dino(session, dino_embedding, limit=settings["dupe_search_limit"])
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


def _embed_asset(asset_id: int, *, semantic: bool, dino: bool) -> None:
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

    The classification signal fires in `finally` on the semantic path: whatever
    goes wrong here, classification must not wait for a signal that never comes.
    """
    from photofant.jobs.classification_pipeline import classification_pipeline

    try:
        _embed_asset_inner(asset_id, semantic=semantic, dino=dino)
    finally:
        if semantic:
            classification_pipeline.signal(asset_id)


def _embed_asset_inner(asset_id: int, *, semantic: bool, dino: bool) -> None:
    """Inner implementation; always called through `_embed_asset`."""
    from PIL import Image as PILImage

    from photofant.inference.image_embedder import resolve_image_embedder
    from photofant.media.asset_paths import resolve_asset_path

    semantic_embedder = resolve_image_embedder() if semantic else None
    dino_embedder = resolve_image_embedder(role="visual_rerank") if dino else None

    if semantic_embedder is None and dino_embedder is None:
        if semantic:
            log.info("No image embedder enabled — skipping embedding for asset %d", asset_id)
        else:
            log.info("No DINOv2 embedder enabled — skipping visual-rerank embedding for asset %d", asset_id)
        return

    asset_path = resolve_asset_path(asset_id)
    if asset_path is None:
        log.warning("Asset %d has no readable file — skipping embedding", asset_id)
        return

    image = np.array(PILImage.open(asset_path).convert("RGB"), dtype=np.uint8)

    semantic_embedding: np.ndarray | None = None
    dino_embedding: np.ndarray | None = None
    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            log.warning("Asset %d not found — skipping embedding persist", asset_id)
            return

        ledger = session.get(ProcessingLedger, asset.content_hash)

        if semantic_embedder is not None:
            semantic_embedding = semantic_embedder.embed(image)
            embeddings.set_semantic(session, asset_id, semantic_embedding)
            upsert_embedding(session, asset_id, semantic_embedding)
            if ledger is not None:
                ledger.embedding_done = True

        if dino_embedder is not None:
            dino_embedding = dino_embedder.embed(image)
            embeddings.set_visual(session, asset_id, dino_embedding)
            upsert_dino_embedding(session, asset_id, dino_embedding)
            if ledger is not None:
                ledger.dino_embedding_done = True
            log.info("Embedded asset %d (DINOv2 %d dims)", asset_id, dino_embedding.shape[0])

        session.commit()

        if dino_embedding is not None:
            _check_for_dupes(session, asset_id, dino_embedding)

    if semantic_embedding is not None:
        log.info("Embedded asset %d (SigLIP2 %d dims)", asset_id, semantic_embedding.shape[0])


def _run_embedding(asset_id: int) -> None:
    """Blocking: embed both active image models (SigLIP2 + DINOv2) for one asset."""
    _embed_asset(asset_id, semantic=True, dino=True)


def _run_dino_embedding(asset_id: int) -> None:
    """Blocking: (re)embed only the DINOv2 visual-rerank space for one asset.

    Lets an existing library gain the DINOv2 embedding on a rerun without
    recomputing SigLIP2 (rerun step ``dino_embedding``).
    """
    _embed_asset(asset_id, semantic=False, dino=True)


async def run_embedding_job(status: JobStatus, asset_id: int) -> None:
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_embedding, asset_id)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_embedding(asset_id: int) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.EMBEDDING,
        label=f"Embedding: Asset {asset_id}",
        coro_factory=lambda job_status: run_embedding_job(job_status, asset_id),
    )
