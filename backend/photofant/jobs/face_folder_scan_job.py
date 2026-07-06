"""Face-folder scan job — auto-register manually placed face images at startup.

Scans all <person>/faces/ subdirectories under data_root. For each image file
whose resolved path is NOT yet registered as a Face.crop_path row, creates a
Face record with origin='manual_original' and the person resolved from the
folder name. Runs at app start so any face images dropped into a person folder
between sessions are picked up automatically.

Skipped files:
  - Already have a Face.crop_path entry → no duplicate
  - Person cannot be resolved from folder name → logged, skipped
  - Located in _unknown/faces/ → always belongs to the unknown person
"""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _collect_face_dirs(data_root: Path) -> list[tuple[Path, int | None]]:
    """Return (faces_dir, person_id_or_None) for each <person>/faces/ directory."""
    from sqlalchemy import select as sa_select

    from photofant.db.models import Person
    from photofant.db.session import SessionLocal
    from photofant.media.person_folders import person_id_from_path

    results: list[tuple[Path, int | None]] = []

    if not data_root.exists():
        return results

    with SessionLocal() as session:
        for entry in data_root.iterdir():
            if not entry.is_dir():
                continue
            faces_dir = entry / "faces"
            if not faces_dir.is_dir():
                continue

            if entry.name == "_unknown":
                unknown = session.scalar(sa_select(Person).where(Person.is_unknown.is_(True)))
                person_id: int | None = unknown.id if unknown else None
            else:
                sample = faces_dir / "_sentinel_"
                person_id = person_id_from_path(sample, data_root, session)

            results.append((faces_dir, person_id))

    return results


def _registered_crop_paths(data_root: Path) -> set[str]:
    """Normalized set of all Face.crop_path values currently in the DB."""
    from photofant.db.models import Face
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        rows = session.query(Face.crop_path).all()
    return {os.path.normcase(str(Path(row[0]).resolve())) for row in rows}


def _import_face_file(
    file_path: Path,
    person_id: int | None,
) -> int | None:
    """Register one face image as a Face record.  Returns the new face_id or None on error."""
    import numpy as np
    from PIL import Image as PILImage

    from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
    from photofant.db.face_vector_index import upsert_embedding
    from photofant.db.models import Face as FaceModel
    from photofant.db.session import SessionLocal
    from photofant.inference.adapters.buffalo_l import resolve_buffalo_l
    from photofant.media.thumbnails import generate_thumbnail

    engine = resolve_buffalo_l()

    # Embedding
    embedding_bytes: bytes | None = None
    if engine is not None:
        try:
            img_pil = PILImage.open(file_path).convert("RGB")
            img_np = np.array(img_pil, dtype=np.uint8)
            emb = engine.embed_crop(img_np)
            if emb is not None:
                embedding_bytes = emb.astype(np.float32).tobytes()
        except Exception:
            log.warning("embed_crop failed for %s", file_path)

    with SessionLocal() as session:
        face_row = FaceModel(
            asset_id=None,
            person_id=person_id,
            crop_path=str(file_path.resolve()),
            embedding=embedding_bytes,
            origin="manual_original",
            created_at=_now_utc(),
        )
        session.add(face_row)
        session.flush()
        face_id = face_row.id
        session.commit()

    # Thumbnail
    try:
        thumb_data = generate_thumbnail(file_path, size=256)
        db_path = get_cache_db_path()
        init_cache_db(db_path)
        store_thumbnail(db_path, face_id, 256, thumb_data, "face")
    except Exception:
        log.warning("Thumbnail failed for face %d (%s)", face_id, file_path)

    # Vector index
    if embedding_bytes is not None:
        try:
            emb_np = np.frombuffer(embedding_bytes, dtype=np.float32).copy()
            with SessionLocal() as vec_session:
                upsert_embedding(vec_session, face_id, emb_np)
                vec_session.commit()
        except Exception:
            log.warning("Vector index upsert failed for face %d", face_id)

    log.info(
        "Registered manual face %d: %s → person_id=%s embedding=%s",
        face_id, file_path.name, person_id, "yes" if embedding_bytes else "no",
    )
    return face_id


def scan_person_face_folders(data_root: Path) -> int:
    """Scan all person face folders and register untracked images.

    Returns the count of newly registered face records.
    """
    registered = _registered_crop_paths(data_root)
    face_dirs = _collect_face_dirs(data_root)

    new_count = 0
    for faces_dir, person_id in face_dirs:
        for file_path in faces_dir.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in _IMAGE_SUFFIXES:
                continue

            norm = os.path.normcase(str(file_path.resolve()))
            if norm in registered:
                continue

            if person_id is None:
                log.warning(
                    "Cannot resolve person for %s — person folder not in DB, skipping",
                    file_path,
                )
                continue

            result = _import_face_file(file_path, person_id)
            if result is not None:
                registered.add(norm)
                new_count += 1

    return new_count


async def run_face_folder_scan_job(status: JobStatus, data_root: Path) -> None:
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    count = await asyncio.to_thread(scan_person_face_folders, data_root)
    log.info("Face-folder scan complete: %d new face(s) registered", count)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_face_folder_scan(data_root: Path) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.FACE,
        label="Gesichter-Ordner: Neuzugänge scannen",
        coro_factory=lambda job_status: run_face_folder_scan_job(job_status, data_root),
    )
