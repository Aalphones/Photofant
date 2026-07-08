"""On-Demand-Scan-Job for duplicate detection via DINOv2 embedding comparison (P37 Phase 4).

Duplicate detection ran on CLIP/SigLIP2 through P36; ADR-024 moved the primary
signal to DINOv2 (visual appearance, not semantic content, is what defines a
duplicate). `dupe_clip_threshold` stays inert in settings for rollback.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from photofant.db.models import Asset, ReviewItem
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)

_COMPARISON_CHUNK_DINO = 1000  # outer-loop rows per thread call for the DINOv2 pairwise scan


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _compare_chunk_dino(
    asset_embeddings: list[tuple[int, bytes]],
    start: int,
    end: int,
    threshold: float,
) -> list[tuple[int, int, float]]:
    """Compare asset_embeddings[start:end] (outer loop) against all asset_embeddings[index+1:].

    Embeddings are already L2-normalized, so cosine similarity is a plain dot
    product. Returns (asset_a_id, asset_b_id, dino_distance) triples where
    a_id < b_id and distance <= threshold.
    """
    asset_ids = [asset_id for asset_id, _ in asset_embeddings]
    vectors = np.stack([
        np.frombuffer(blob, dtype=np.float32) for _, blob in asset_embeddings
    ])

    chunk = vectors[start:end]
    similarities = chunk @ vectors.T
    distances = 1.0 - similarities

    found: list[tuple[int, int, float]] = []
    for local_row, global_i in enumerate(range(start, end)):
        asset_id_i = asset_ids[global_i]
        for global_j in range(global_i + 1, len(asset_ids)):
            distance = float(distances[local_row, global_j])
            if distance <= threshold:
                asset_id_j = asset_ids[global_j]
                found.append((
                    min(asset_id_i, asset_id_j),
                    max(asset_id_i, asset_id_j),
                    distance,
                ))
    return found


def _purge_unresolved_dupe_candidates() -> None:
    """Delete unresolved dupe-candidate ReviewItems before a fresh full scan.

    A full scan re-derives the whole candidate set from current settings/thresholds,
    so stale unresolved candidates from a previous (e.g. looser) threshold would
    otherwise pile up indefinitely. Manually resolved pairs are untouched.
    """
    with SessionLocal() as session:
        session.execute(
            delete(ReviewItem).where(
                ReviewItem.type == "dupe_candidate",
                ReviewItem.resolved_at.is_(None),
            )
        )
        session.commit()


def _insert_pairs(pairs: list[tuple[int, int, float]]) -> None:
    """Persist (asset_a_id, asset_b_id, dino_distance) tuples into `clip_distance` (inert column name)."""
    with SessionLocal() as session:
        for asset_a_id, asset_b_id, dino_distance in pairs:
            stmt = sqlite_insert(ReviewItem).values(
                type="dupe_candidate",
                asset_a_id=asset_a_id,
                asset_b_id=asset_b_id,
                clip_distance=dino_distance,
                created_at=_now_utc(),
            ).on_conflict_do_nothing()
            session.execute(stmt)
        session.commit()


async def run_dupe_scan_job(
    status: JobStatus,
    scope: str,
    asset_ids: list[int] | None,
) -> None:
    from photofant.settings import load_settings

    settings = load_settings()
    dino_enabled: bool = settings["dupe_clip_enabled"]
    dino_threshold: float = settings["dupe_dino_threshold"]

    if scope != "selection":
        await asyncio.to_thread(_purge_unresolved_dupe_candidates)
        log.info("dupe_scan: purged unresolved dupe-candidate items before full scan")

    dino_assets: list[tuple[int, bytes]] = []
    if dino_enabled:
        with SessionLocal() as session:
            dino_query = select(Asset.id, Asset.dino_embedding).where(
                Asset.dino_embedding.is_not(None)
            )
            if scope == "selection" and asset_ids:
                dino_query = dino_query.where(Asset.id.in_(asset_ids))
            dino_assets = [
                (asset_id, bytes(blob)) for asset_id, blob in session.execute(dino_query).all()
            ]

    if not dino_assets:
        log.info(
            "dupe_scan: nothing to compare (dupe_enabled=%s, scope=%s)", dino_enabled, scope,
        )
        return

    # (asset_a_id, asset_b_id) -> dino_distance.
    found: dict[tuple[int, int], float] = {}

    total = len(dino_assets)
    log.info("dupe_scan: DINOv2 comparing %d assets (scope=%s, threshold=%.3f)", total, scope, dino_threshold)
    for chunk_start in range(0, total, _COMPARISON_CHUNK_DINO):
        chunk_end = min(chunk_start + _COMPARISON_CHUNK_DINO, total)
        dino_chunk_pairs = await asyncio.to_thread(
            _compare_chunk_dino, dino_assets, chunk_start, chunk_end, dino_threshold
        )
        for asset_a_id, asset_b_id, dino_distance in dino_chunk_pairs:
            found[(asset_a_id, asset_b_id)] = dino_distance
        job_queue.update(status, progress=0.9 * chunk_end / total, state=JobState.RUNNING)

    if found:
        pairs = [
            (asset_a_id, asset_b_id, dino_distance)
            for (asset_a_id, asset_b_id), dino_distance in found.items()
        ]
        await asyncio.to_thread(_insert_pairs, pairs)
        log.info("dupe_scan: inserted up to %d new dupe-candidate pair(s)", len(pairs))

    job_queue.update(status, progress=0.99, state=JobState.RUNNING)


async def enqueue_dupe_scan(scope: str, asset_ids: list[int] | None = None) -> JobStatus:
    if scope == "selection" and asset_ids:
        label = f"Duplikate prüfen ({len(asset_ids)} Bilder)"
    else:
        label = "Duplikate scannen (vollständig)"
    return await job_queue.enqueue(
        kind=JobKind.DUPE_SCAN,
        label=label,
        coro_factory=lambda job_status: run_dupe_scan_job(job_status, scope, asset_ids),
    )
