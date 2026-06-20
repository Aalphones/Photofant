"""Heuristics job — computes quality_score (resolution + sharpness) for one asset.

One job per asset; controlled by ProcessingLedger.heuristics_done (run exactly once
in normal import flow; ledger flag reset by rerun endpoint for selective re-computation).

quality_score ∈ [0, 1]:
  - resolution_score = min(1.0, (W * H) / _REFERENCE_PIXELS)   (FHD = 1.0)
  - sharpness_score  = min(1.0, laplacian_variance / blur_threshold)   (blur_threshold from settings)
  - quality_score    = 0.5 * resolution_score + 0.5 * sharpness_score

Laplacian variance is computed via numpy finite-differences (no OpenCV dependency).
"""
from __future__ import annotations

import logging

import numpy as np

from photofant.db.models import Asset, Face, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)

_REFERENCE_PIXELS: int = 1920 * 1080


def _laplacian_variance(gray: np.ndarray) -> float:
    """Estimate sharpness via Laplacian variance (finite-difference approximation)."""
    lap_y = gray[:-2, :].astype(np.float32) - 2.0 * gray[1:-1, :] + gray[2:, :]
    lap_x = gray[:, :-2].astype(np.float32) - 2.0 * gray[:, 1:-1] + gray[:, 2:]
    lap = lap_y[:, 1:-1] + lap_x[1:-1, :]
    return float(np.var(lap))


def _compute_quality(image: np.ndarray, blur_threshold: float) -> float:
    height, width = image.shape[:2]
    resolution_score = min(1.0, (width * height) / _REFERENCE_PIXELS)

    gray = np.mean(image, axis=2) if image.ndim == 3 else image.astype(np.float32)
    sharpness_score = min(1.0, _laplacian_variance(gray) / blur_threshold)

    quality: float = round(0.5 * resolution_score + 0.5 * sharpness_score, 4)
    return quality


def _compute_framing(asset_id: int, image_width: int, image_height: int) -> str | None:
    """Determine framing from largest face BBox relative to image area.

    close_up  : face area > 15 % of image
    medium    : face area 4–15 %
    full_body : face area < 4 % (or no detected faces → left as None)
    """
    if image_width <= 0 or image_height <= 0:
        return None

    image_area = image_width * image_height

    with SessionLocal() as session:
        faces = session.query(Face).filter(Face.asset_id == asset_id).all()

    if not faces:
        return None

    max_ratio = 0.0
    for face in faces:
        bbox = face.bbox
        if not bbox:
            continue
        x1 = float(bbox.get("x1", 0))
        y1 = float(bbox.get("y1", 0))
        x2 = float(bbox.get("x2", 0))
        y2 = float(bbox.get("y2", 0))
        face_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        ratio = face_area / image_area
        if ratio > max_ratio:
            max_ratio = ratio

    if max_ratio > 0.15:
        return "close_up"
    if max_ratio > 0.04:
        return "medium"
    return "full_body"


def _run_heuristics(asset_id: int, asset_path: str) -> None:
    """Blocking: compute quality_score + framing and persist them for one asset."""
    from PIL import Image as PILImage

    from photofant.settings import load_settings

    blur_threshold = load_settings()["blur_threshold"]
    image = np.array(PILImage.open(asset_path).convert("RGB"), dtype=np.uint8)
    quality = _compute_quality(image, blur_threshold)

    height, width = image.shape[:2]
    framing = _compute_framing(asset_id, width, height)

    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            log.warning("Asset %d not found — skipping heuristics persist", asset_id)
            return

        asset.quality_score = quality
        if framing is not None:
            asset.framing = framing

        ledger = session.get(ProcessingLedger, asset.content_hash)
        if ledger is not None:
            ledger.heuristics_done = True

        session.commit()

    log.info("Heuristics done for asset %d: quality_score=%.4f framing=%s", asset_id, quality, framing)


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
