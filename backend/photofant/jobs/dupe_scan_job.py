"""On-Demand-Scan-Job for duplicate detection via pHash comparison."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from photofant.db.models import Asset, ReviewItem
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.media.phash import hamming_distance

log = logging.getLogger(__name__)

_COMPARISON_CHUNK = 200  # outer-loop rows per thread call — yields event-loop breaks


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _compare_chunk(
    assets: list[tuple[int, int]],
    start: int,
    end: int,
    threshold: int,
) -> list[tuple[int, int, int]]:
    """Compare assets[start:end] (outer loop) against all assets[index+1:].

    Returns (asset_a_id, asset_b_id, distance) triples where a_id < b_id.
    Each unique pair is generated exactly once across all chunks.
    """
    total = len(assets)
    found: list[tuple[int, int, int]] = []
    for i in range(start, end):
        asset_id_i, phash_i = assets[i]
        for j in range(i + 1, total):
            asset_id_j, phash_j = assets[j]
            distance = hamming_distance(phash_i, phash_j)
            if distance <= threshold:
                found.append((
                    min(asset_id_i, asset_id_j),
                    max(asset_id_i, asset_id_j),
                    distance,
                ))
    return found


def _insert_pairs(pairs: list[tuple[int, int, int]]) -> None:
    """Persist (asset_a_id, asset_b_id, phash_distance) triples; skip conflicts."""
    with SessionLocal() as session:
        for asset_a_id, asset_b_id, distance in pairs:
            stmt = sqlite_insert(ReviewItem).values(
                type="dupe_candidate",
                asset_a_id=asset_a_id,
                asset_b_id=asset_b_id,
                phash_distance=distance,
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
    threshold: int = settings["dupe_threshold"]

    with SessionLocal() as session:
        query = select(Asset.id, Asset.phash).where(Asset.phash.is_not(None))
        if scope == "selection" and asset_ids:
            query = query.where(Asset.id.in_(asset_ids))
        rows = session.execute(query).all()

    assets: list[tuple[int, int]] = list(rows)
    total = len(assets)

    if total == 0:
        log.info("dupe_scan: no assets with pHash found (scope=%s)", scope)
        return

    log.info("dupe_scan: comparing %d assets (scope=%s, threshold=%d)", total, scope, threshold)

    found_pairs: list[tuple[int, int, int]] = []

    for chunk_start in range(0, total, _COMPARISON_CHUNK):
        chunk_end = min(chunk_start + _COMPARISON_CHUNK, total)
        chunk_pairs = await asyncio.to_thread(
            _compare_chunk, assets, chunk_start, chunk_end, threshold
        )
        found_pairs.extend(chunk_pairs)
        job_queue.update(status, progress=0.9 * chunk_end / total, state=JobState.RUNNING)

    if found_pairs:
        await asyncio.to_thread(_insert_pairs, found_pairs)
        log.info("dupe_scan: inserted up to %d new dupe-candidate pair(s)", len(found_pairs))

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
