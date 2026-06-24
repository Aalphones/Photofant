"""Face job — detect faces, extract crops + embeddings for one asset.

One job per asset; gated on ProcessingLedger.faces_done and the buffalo_l
model being enabled.  Skips silently when the model is not available so the
rest of the import pipeline continues unaffected.

Output:
  - Crop file: <data_root>/_unknown/faces/<asset_id>_<index>.jpg
  - Face row in DB (crop_path, bbox, embedding, phash, score, age)
  - Thumbnail in cache DB (target_kind='face')
  - ProcessingLedger.faces_done = True
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from photofant.db.models import AssetInstance, Face, Person, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)

_CROP_JPEG_QUALITY = 92


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _crop_square(
    image: np.ndarray,
    bbox: list[float],
    padding: int,
) -> np.ndarray:
    """Crop face as a 1:1 square centered on bbox + padding.

    Out-of-bounds regions are filled with black so the output is always square.
    """
    img_h, img_w = image.shape[:2]
    x1, y1, x2, y2 = (int(round(v)) for v in bbox)
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    half = max(x2 - x1, y2 - y1) // 2 + padding
    side = 2 * half

    src_x1 = max(0, cx - half)
    src_y1 = max(0, cy - half)
    src_x2 = min(img_w, cx + half)
    src_y2 = min(img_h, cy + half)

    dst_x = src_x1 - (cx - half)
    dst_y = src_y1 - (cy - half)

    canvas = np.zeros((side, side, 3), dtype=np.uint8)
    canvas[dst_y : dst_y + (src_y2 - src_y1), dst_x : dst_x + (src_x2 - src_x1)] = (
        image[src_y1:src_y2, src_x1:src_x2]
    )
    return canvas


def _save_crop(crop: np.ndarray, dest: Path) -> None:
    from PIL import Image as PILImage

    dest.parent.mkdir(parents=True, exist_ok=True)
    PILImage.fromarray(crop).save(str(dest), "JPEG", quality=_CROP_JPEG_QUALITY)


def _generate_face_thumbnail(crop_path: Path) -> bytes:
    from photofant.media.thumbnails import generate_thumbnail

    return generate_thumbnail(crop_path, size=256)


def _store_face_thumbnail(face_id: int, data: bytes) -> None:
    from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail

    db_path = get_cache_db_path()
    init_cache_db(db_path)
    store_thumbnail(db_path, face_id, size=256, data=data, target_kind="face")


def _compute_crop_phash(crop_path: Path) -> str | None:
    try:
        import imagehash
        from PIL import Image as PILImage

        img = PILImage.open(crop_path).convert("RGB")
        return str(imagehash.dhash(img, hash_size=8))
    except Exception:
        log.exception("pHash failed for face crop %s", crop_path)
        return None


def _embedding_to_bytes(embedding: np.ndarray | None) -> bytes | None:
    if embedding is None:
        return None
    return embedding.astype(np.float32).tobytes()


def _upsert_face_vector(face_id: int, embedding: np.ndarray) -> None:
    from photofant.db.face_vector_index import upsert_embedding

    with SessionLocal() as session:
        upsert_embedding(session, face_id, embedding)
        session.commit()


def _run_incremental_match(face_id: int) -> None:
    from photofant.jobs.clustering_job import run_incremental_match

    run_incremental_match(face_id)


def _run_face_job(asset_id: int, asset_path: str) -> None:
    from photofant.config import get_data_root
    from photofant.inference.adapters.buffalo_l import resolve_buffalo_l
    from photofant.settings import load_settings

    engine = resolve_buffalo_l()
    if engine is None:
        log.info("Face job skipped for asset %d — buffalo_l not available", asset_id)
        _mark_done(asset_id)
        return

    settings = load_settings()
    padding = int(settings.get('face_crop_padding', 40))
    conf_threshold = float(settings.get('face_det_conf_threshold', 0.5))
    iou_threshold = float(settings.get('face_det_iou_threshold', 0.45))

    from PIL import Image as PILImage

    image_pil = PILImage.open(asset_path).convert("RGB")
    image = np.array(image_pil, dtype=np.uint8)

    try:
        faces = engine.detect(image, conf_threshold=conf_threshold, iou_threshold=iou_threshold)
    except Exception:
        log.exception("buffalo_l detection failed for asset %d", asset_id)
        _mark_done(asset_id)
        return

    if not faces:
        log.info("No faces detected in asset %d", asset_id)
        _mark_done(asset_id)
        return

    data_root = get_data_root()
    faces_dir = data_root / "_unknown" / "faces"
    faces_dir.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as session:
        unknown_person = session.query(Person).filter_by(is_unknown=True).first()
        if unknown_person is None:
            log.error("_unknown person row missing — cannot save faces")
            return
        unknown_person_id = unknown_person.id

        # Single face + fixed_person upload → assign directly to the known person.
        fixed_person_id: int | None = None
        if len(faces) == 1:
            from sqlalchemy import select as sa_select
            fixed_instance = session.scalar(
                sa_select(AssetInstance).where(
                    AssetInstance.asset_id == asset_id,
                    AssetInstance.fixed_person.is_(True),
                    AssetInstance.deleted_at.is_(None),
                )
            )
            if fixed_instance is not None:
                fixed_person_id = fixed_instance.person_id

    for face_index, face_dict in enumerate(faces):
        bbox = face_dict["bbox"]
        score = face_dict.get("score")
        age = face_dict.get("age")
        embedding = face_dict.get("embedding")

        crop_np = _crop_square(image, bbox, padding)
        crop_filename = f"{asset_id}_{face_index}.jpg"
        crop_path = faces_dir / crop_filename

        try:
            _save_crop(crop_np, crop_path)
        except Exception:
            log.exception("Failed to save face crop for asset %d index %d", asset_id, face_index)
            continue

        crop_phash = _compute_crop_phash(crop_path)
        resolution = crop_np.shape[0] * crop_np.shape[1]

        with SessionLocal() as session:
            face_row = Face(
                asset_id=asset_id,
                person_id=fixed_person_id if fixed_person_id is not None else unknown_person_id,
                crop_path=str(crop_path.resolve()),
                bbox={"x1": bbox[0], "y1": bbox[1], "x2": bbox[2], "y2": bbox[3]},
                padding=padding,
                embedding=_embedding_to_bytes(embedding),
                phash=crop_phash,
                score=score,
                age=age,
                origin="derived",
                origin_type="original",
                is_upscaled=False,
                resolution=resolution,
                created_at=_now_utc(),
            )
            session.add(face_row)
            session.flush()
            face_id = face_row.id
            session.commit()

        # Thumbnail (after commit so face_id is stable)
        try:
            thumb_data = _generate_face_thumbnail(crop_path)
            _store_face_thumbnail(face_id, thumb_data)
        except Exception:
            log.exception("Face thumbnail failed for face %d", face_id)

        # Vector index + incremental matching
        if embedding is not None:
            try:
                _upsert_face_vector(face_id, embedding)
            except Exception:
                log.exception("Face vector index upsert failed for face %d", face_id)
            try:
                _run_incremental_match(face_id)
            except Exception:
                log.exception("Incremental match failed for face %d", face_id)

        log.info(
            "Face %d saved: asset=%d idx=%d score=%.3f age=%s",
            face_id, asset_id, face_index, score or 0.0, age,
        )

    _update_framing(asset_id, image.shape[1], image.shape[0])
    _mark_done(asset_id)


def _update_framing(asset_id: int, image_width: int, image_height: int) -> None:
    """Recompute asset.framing from detected faces (runs after all faces are saved)."""
    from photofant.jobs.heuristics_job import _compute_framing

    framing = _compute_framing(asset_id, image_width, image_height)
    if framing is None:
        return
    with SessionLocal() as session:
        from photofant.db.models import Asset as AssetModel
        asset = session.get(AssetModel, asset_id)
        if asset is not None:
            asset.framing = framing
            session.commit()
    log.info("Framing updated for asset %d: %s", asset_id, framing)


def _mark_done(asset_id: int) -> None:
    from photofant.db.models import Asset

    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            return
        ledger = session.get(ProcessingLedger, asset.content_hash)
        if ledger is not None:
            ledger.faces_done = True
        session.commit()


async def run_face_job(status: JobStatus, asset_id: int, asset_path: str) -> None:
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_face_job, asset_id, asset_path)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_face(asset_id: int, asset_path: str) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.FACE,
        label=f"Gesichter: Asset {asset_id}",
        coro_factory=lambda job_status: run_face_job(job_status, asset_id, asset_path),
    )
