"""Rerun job — bulk reprocessing of classification steps for existing assets.

Resets the selected ProcessingLedger flags for each target asset, then
re-runs the corresponding steps sequentially. A single batch job provides
clean progress reporting; the Ledger guarantees idempotent re-entry if the
job is interrupted.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from sqlalchemy import select

from photofant.db.models import Asset, AssetInstance, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)

ClassifyStep = Literal[
    "tags", "caption", "embedding", "dino_embedding", "heuristics", "faces", "categories"
]

_STEP_FLAGS: dict[str, str] = {
    "tags": "tags_done",
    "caption": "caption_done",
    "embedding": "embedding_done",
    "dino_embedding": "dino_embedding_done",  # P37: DINOv2-only re-embed (SigLIP2 untouched)
    "heuristics": "heuristics_done",
    "faces": "faces_done",
    "categories": "classified",
}


def _resolve_assets(
    asset_ids: list[int] | Literal["all"],
) -> list[tuple[int, str]]:
    """Return list of (asset_id, content_hash) for non-deleted active assets.

    No path here on purpose — each step resolves the file itself, right before
    reading it. A bulk rerun runs for hours and outlives plenty of file moves.
    """
    with SessionLocal() as session:
        query = (
            select(Asset.id, Asset.content_hash)
            .join(AssetInstance, AssetInstance.asset_id == Asset.id)
            .where(AssetInstance.deleted_at.is_(None))
            .where(AssetInstance.missing_at.is_(None))
            .distinct()
        )
        if asset_ids != "all":
            query = query.where(Asset.id.in_(asset_ids))
        rows = session.execute(query).all()
    return [(int(row[0]), str(row[1])) for row in rows]


def _delete_existing_faces(asset_id: int) -> None:
    """Remove all derived Face rows (+ crops, vector index, thumbnails) for an asset.

    Leaves manual_original faces untouched (they have asset_id=None anyway).
    Call this before re-running face detection to avoid duplicates.
    """
    from pathlib import Path

    from photofant.db.cache import delete_thumbnails, get_cache_db_path
    from photofant.db.face_vector_index import delete_embedding
    from photofant.db.models import Face

    with SessionLocal() as session:
        faces = (
            session.query(Face)
            .filter(Face.asset_id == asset_id)
            .filter(Face.origin != "manual_original")
            .all()
        )
        if not faces:
            return

        cache_db = get_cache_db_path()
        for face in faces:
            # crop file
            crop = Path(face.crop_path)
            if crop.exists():
                try:
                    crop.unlink()
                except OSError:
                    log.warning("Could not delete face crop %s", crop)
            # vector index
            try:
                delete_embedding(session, face.id)
            except Exception:
                log.exception("Vector index delete failed for face %d", face.id)
            # thumbnail cache
            try:
                delete_thumbnails(cache_db, face.id, target_kind="face")
            except Exception:
                log.exception("Thumbnail delete failed for face %d", face.id)

        for face in faces:
            session.delete(face)
        session.commit()

    log.info("Deleted %d existing face(s) for asset %d before re-extraction", len(faces), asset_id)


def _reset_ledger_flags(content_hash: str, steps: list[ClassifyStep]) -> None:
    with SessionLocal() as session:
        ledger = session.get(ProcessingLedger, content_hash)
        if ledger is None:
            return
        for step in steps:
            flag_name = _STEP_FLAGS.get(step)
            if flag_name is not None:
                setattr(ledger, flag_name, False)
        session.commit()


async def run_rerun_job(
    status: JobStatus,
    asset_ids: list[int] | Literal["all"],
    steps: list[ClassifyStep],
    caption_preset_id: int | None,
) -> None:
    from photofant.jobs.caption_job import _run_caption_with_preset
    from photofant.jobs.classification_job import _run_classification
    from photofant.jobs.embedding_job import _run_dino_embedding, _run_embedding
    from photofant.jobs.face_job import _run_face_job
    from photofant.jobs.heuristics_job import _run_heuristics
    from photofant.jobs.tagging_job import _run_tagging

    assets = await asyncio.to_thread(_resolve_assets, asset_ids)
    total = max(len(assets), 1)

    job_queue.update(status, progress=0.0, state=JobState.RUNNING)

    for index, (asset_id, content_hash) in enumerate(assets):
        await asyncio.to_thread(_reset_ledger_flags, content_hash, steps)

        if "heuristics" in steps:
            await asyncio.to_thread(_run_heuristics, asset_id)
        if "tags" in steps:
            await asyncio.to_thread(_run_tagging, asset_id)
        if "caption" in steps:
            await asyncio.to_thread(_run_caption_with_preset, asset_id, caption_preset_id, True)
        if "embedding" in steps:
            await asyncio.to_thread(_run_embedding, asset_id)
        elif "dino_embedding" in steps:
            # DINOv2-only re-embed — skipped when the full embedding step already ran both.
            await asyncio.to_thread(_run_dino_embedding, asset_id)
        if "categories" in steps:
            await asyncio.to_thread(_run_classification, asset_id)
        if "faces" in steps:
            await asyncio.to_thread(_delete_existing_faces, asset_id)
            await asyncio.to_thread(_run_face_job, asset_id)

        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)

    log.info("Rerun done: %d asset(s), steps=%s", len(assets), steps)


async def enqueue_rerun(
    asset_ids: list[int] | Literal["all"],
    steps: list[ClassifyStep],
    caption_preset_id: int | None,
) -> JobStatus:
    count = "alle" if asset_ids == "all" else str(len(asset_ids))
    steps_label = ", ".join(steps)
    return await job_queue.enqueue(
        kind=JobKind.RERUN,
        label=f"Rerun {count} Bild(er): {steps_label}",
        coro_factory=lambda job_status: run_rerun_job(job_status, asset_ids, steps, caption_preset_id),
    )
