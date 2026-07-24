from __future__ import annotations

import logging
from typing import Literal

from photofant.db.cache import clear_cache, get_cache_db_path, init_cache_db
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.jobs.thumbnail_job import gather_active_asset_ids, generate_thumbnails

log = logging.getLogger(__name__)

RebuildTarget = Literal["thumbnails", "embeddings", "faces", "knowledge", "knowledge_reconcile"]

_TARGET_LABELS: dict[str, str] = {
    "thumbnails": "Thumbnails neu aufbauen",
    "embeddings": "Vektor-Index neu aufbauen",
    "faces": "Face-Crops neu extrahieren",
    "knowledge": "Wissens-Cache neu aufbauen",
    "knowledge_reconcile": "Notiz-Änderungen übernehmen",
}


async def _rebuild_thumbnails(status: JobStatus) -> None:
    """Drop the whole thumbnail cache and regenerate it from the source images.

    Safe to interrupt: thumbnails are pure cache (originals are never touched)
    and any not yet regenerated are recreated lazily on first request.
    """
    db_path = get_cache_db_path()
    init_cache_db(db_path)
    clear_cache(db_path)

    asset_ids = gather_active_asset_ids()
    await generate_thumbnails(status, db_path, asset_ids)
    log.info("Thumbnail cache rebuilt for %d assets", len(asset_ids))


async def _rebuild_embeddings(status: JobStatus) -> None:
    """Rebuild the sqlite-vec vector index from the canonical semantic vectors.

    Source is the ``photofant/db/embeddings`` access layer (``asset_embedding`` side
    table, migration 0043) — not the legacy asset column.
    """
    import asyncio

    from photofant.db.vector_index import rebuild_index

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)

    def _do_rebuild() -> int:
        with SessionLocal() as session:
            return rebuild_index(session)

    count = await asyncio.to_thread(_do_rebuild)
    log.info("Vector index rebuilt: %d embedding(s)", count)


def _rebuild_faces_sync() -> int:
    """Re-crop all derived face crops from their source images.

    Skips faces with origin='manual_original' — those are user-provided and
    must never be overwritten. Returns the number of re-extracted crops.
    """
    from pathlib import Path as _Path

    import numpy as np
    from PIL import Image as PILImage
    from sqlalchemy import select

    from photofant.db.models import AssetInstance, Face

    with SessionLocal() as session:
        face_rows = session.execute(
            select(Face.id, Face.asset_id, Face.crop_path, Face.bbox, Face.padding)
            .where(
                Face.origin != "manual_original",
                Face.asset_id.is_not(None),
            )
        ).all()

        # Build a map: asset_id → first active instance path
        asset_ids = list({int(row[1]) for row in face_rows})
        if not asset_ids:
            return 0

        instance_rows = session.execute(
            select(AssetInstance.asset_id, AssetInstance.path)
            .where(
                AssetInstance.asset_id.in_(asset_ids),
                AssetInstance.deleted_at.is_(None),
            )
        ).all()

    path_map: dict[int, str] = {}
    for asset_id, path in instance_rows:
        if int(asset_id) not in path_map:
            path_map[int(asset_id)] = path

    rebuilt = 0
    for face_id, asset_id, crop_path, bbox, padding in face_rows:
        source = path_map.get(int(asset_id))
        if source is None:
            continue
        try:
            with PILImage.open(source) as raw:
                image = np.array(raw.convert("RGB"), dtype=np.uint8)

            if bbox:
                pad = padding or 40
                x1 = max(0, int(bbox.get("x1", 0)) - pad)
                y1 = max(0, int(bbox.get("y1", 0)) - pad)
                x2 = min(image.shape[1], int(bbox.get("x2", image.shape[1])) + pad)
                y2 = min(image.shape[0], int(bbox.get("y2", image.shape[0])) + pad)
                crop = image[y1:y2, x1:x2]
            else:
                crop = image

            dest = _Path(crop_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            PILImage.fromarray(crop).save(str(dest), "JPEG", quality=92)
            rebuilt += 1
        except Exception:
            log.exception("Face rebuild failed for face %d (asset %d)", face_id, asset_id)

    return rebuilt


async def _rebuild_faces(status: JobStatus) -> None:
    """Re-extract derived face crops from source images (async wrapper)."""
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    count = await asyncio.to_thread(_rebuild_faces_sync)
    log.info("Face rebuild complete: %d crops re-extracted", count)


async def _sync_knowledge(status: JobStatus, mode: Literal["rebuild", "reconcile"]) -> None:
    """Rebuild or reconcile the knowledge cache from the markdown vault (async wrapper).

    The heavy lifting is the pure sync core in ``knowledge/maintenance.py``; here we only
    open the vault, run it off the event loop and commit. Markdown is the truth, the cache
    is fully rebuildable from it (P22 contract).
    """
    import asyncio

    from photofant.knowledge.maintenance import rebuild_cache, reconcile_cache
    from photofant.knowledge.vault import open_vault

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)

    def _do_sync() -> str:
        vault = open_vault()
        with SessionLocal() as session:
            if mode == "rebuild":
                result = rebuild_cache(session, vault)
            else:
                result = reconcile_cache(session, vault)
            session.commit()
        return f"{result.imported} imported, {result.removed} removed, {result.failed} failed"

    summary = await asyncio.to_thread(_do_sync)
    log.info("Knowledge %s complete: %s", mode, summary)


async def run_rebuild_job(status: JobStatus, target: RebuildTarget) -> None:
    if target == "thumbnails":
        await _rebuild_thumbnails(status)
    elif target == "embeddings":
        await _rebuild_embeddings(status)
    elif target == "faces":
        await _rebuild_faces(status)
    elif target == "knowledge":
        await _sync_knowledge(status, "rebuild")
    elif target == "knowledge_reconcile":
        await _sync_knowledge(status, "reconcile")
    else:  # pragma: no cover - guarded by the API Literal
        raise ValueError(f"unknown rebuild target '{target}'")

    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_rebuild(target: RebuildTarget) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.REBUILD,
        label=_TARGET_LABELS.get(target, f"Rebuild: {target}"),
        coro_factory=lambda job_status: run_rebuild_job(job_status, target),
    )
