"""Heuristics job — computes quality_score (resolution + sharpness) for one asset.

One job per asset; controlled by ProcessingLedger.heuristics_done (run exactly once
in normal import flow; ledger flag reset by rerun endpoint for selective re-computation).

quality_score ∈ [0, 1]:
  - resolution_score = min(1.0, (W * H) / _REFERENCE_PIXELS)   (FHD = 1.0)
  - sharpness_score  = min(1.0, laplacian_variance / _REFERENCE_SHARPNESS)
  - quality_score    = 0.5 * resolution_score + 0.5 * sharpness_score

Laplacian variance is computed via numpy finite-differences (no OpenCV dependency).
"""
from __future__ import annotations

import logging

import numpy as np

from photofant.db.models import Asset, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)

_REFERENCE_PIXELS: int = 1920 * 1080
_REFERENCE_SHARPNESS: float = 200.0


def _laplacian_variance(gray: np.ndarray) -> float:
    """Estimate sharpness via Laplacian variance (finite-difference approximation)."""
    lap_y = gray[:-2, :].astype(np.float32) - 2.0 * gray[1:-1, :] + gray[2:, :]
    lap_x = gray[:, :-2].astype(np.float32) - 2.0 * gray[:, 1:-1] + gray[:, 2:]
    lap = lap_y[:, 1:-1] + lap_x[1:-1, :]
    return float(np.var(lap))


def _compute_quality(image: np.ndarray) -> float:
    height, width = image.shape[:2]
    resolution_score = min(1.0, (width * height) / _REFERENCE_PIXELS)

    gray = np.mean(image, axis=2) if image.ndim == 3 else image.astype(np.float32)
    sharpness_score = min(1.0, _laplacian_variance(gray) / _REFERENCE_SHARPNESS)

    return round(0.5 * resolution_score + 0.5 * sharpness_score, 4)


def _run_heuristics(asset_id: int, asset_path: str) -> None:
    """Blocking: compute quality_score and persist it for one asset."""
    from PIL import Image as PILImage

    image = np.array(PILImage.open(asset_path).convert("RGB"), dtype=np.uint8)
    quality = _compute_quality(image)

    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            log.warning("Asset %d not found — skipping heuristics persist", asset_id)
            return

        asset.quality_score = quality

        ledger = session.get(ProcessingLedger, asset.content_hash)
        if ledger is not None:
            ledger.heuristics_done = True

        session.commit()

    log.info("Heuristics done for asset %d: quality_score=%.4f", asset_id, quality)


async def run_heuristics_job(status: JobStatus, asset_id: int, asset_path: str) -> None:
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_heuristics, asset_id, asset_path)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_heuristics(asset_id: int, asset_path: str) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.HEURISTICS,
        label=f"Heuristiken: Asset {asset_id}",
        coro_factory=lambda job_status: run_heuristics_job(job_status, asset_id, asset_path),
    )
