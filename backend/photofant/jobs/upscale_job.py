"""Upscale job — GPU-based image upscaling via SeedVR2 (P9 Phase 3).

POST /api/assets/{id}/upscale  →  enqueues this job.

Flow:
  1. Resolve asset → get source file path.
  2. Load SeedVR2 from the registry (or first enabled upscaler model).
  3. Run upscale; save result to person's edits/ folder.
  4. Create Version(type="upscale", is_current=True).
  5. Face dedupe rule (§8.3): mark existing face crops for this asset as
     superseded by the upscaled source; re-run face detection on the upscaled
     file so new crops get is_upscaled=True.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from photofant.db.models import AssetInstance, Face, Person, Version
from photofant.db.session import SessionLocal
from photofant.inference.generative_engine import GenerativeAvailability, check_generative_available, generative_engine
from photofant.inference.seedvr2_upscaler import SeedVR2Upscaler
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.media.person_folders import ensure_person_folder

log = logging.getLogger(__name__)


# ── Model resolution ──────────────────────────────────────────────────────────

def _resolve_upscaler_path(model_id: str | None) -> tuple[str, str] | None:
    """Return (manifest_id, model_path) for the requested or first enabled upscaler."""
    from photofant.db.models import ModelRegistry

    with SessionLocal() as session:
        if model_id:
            row = session.query(ModelRegistry).filter_by(manifest_id=model_id, enabled=True).first()
            if row and row.path and Path(row.path).exists():
                return (row.manifest_id, row.path)
            return None

        row = (
            session.query(ModelRegistry)
            .filter_by(role="upscaler", enabled=True)
            .first()
        )
        if row and row.path and Path(row.path).exists():
            return (row.manifest_id, row.path)
    return None


# ── Asset resolution ──────────────────────────────────────────────────────────

def _resolve_asset(asset_id: int) -> tuple[int, int, str] | None:
    """Return (instance_id, person_id, source_path) for the active asset."""
    from photofant.db.models import Asset

    with SessionLocal() as session:
        row = (
            session.query(AssetInstance.id, AssetInstance.person_id, AssetInstance.path)
            .join(Asset, Asset.id == AssetInstance.asset_id)
            .filter(Asset.id == asset_id)
            .filter(AssetInstance.deleted_at.is_(None))
            .first()
        )
    if row is None:
        return None
    return (int(row[0]), int(row[1]), str(row[2]))


# ── Version helpers ───────────────────────────────────────────────────────────

def _create_upscale_version(
    instance_id: int,
    person_id: int,
    edit_path: Path,
    width: int,
    height: int,
    model_id: str,
    scale: int,
    params: dict[str, Any],
) -> int:
    """Write upscale Version row; return version.id."""
    from photofant.config import get_data_root

    data_root = Path(get_data_root())
    with SessionLocal() as session:
        person = session.get(Person, person_id)
        if person is None:
            raise ValueError(f"Person {person_id} not found")
        person_dir = ensure_person_folder(data_root, person)

    edits_dir = person_dir / "edits"
    edits_dir.mkdir(parents=True, exist_ok=True)

    # Mark existing current versions as non-current
    with SessionLocal() as session:
        for ver in (
            session.query(Version)
            .filter(Version.instance_id == instance_id, Version.is_current.is_(True))
            .all()
        ):
            ver.is_current = False

        version = Version(
            instance_id=instance_id,
            face_id=None,
            type="upscale",
            parent_id=None,
            path=str(edit_path.resolve()),
            is_current=True,
            params={
                "model_id": model_id,
                "scale": scale,
                "width": width,
                "height": height,
                **params,
            },
            created_at=datetime.now(UTC),
        )
        session.add(version)
        session.commit()
        return int(version.id)


# ── Face dedupe rule (§8.3) ───────────────────────────────────────────────────

def _apply_face_dedupe_upscale_rule(asset_id: int, version_id: int) -> None:
    """Mark existing face crops as superseded by the upscaled version.

    Sets origin_type='superseded_by_upscale' on existing face rows so that
    future face re-detection can distinguish old (low-res) from new (upscaled)
    crops. Does NOT delete existing faces — they remain visible until a face
    re-detection job refreshes them with is_upscaled=True crops from the new
    version file.
    """
    with SessionLocal() as session:
        faces = session.query(Face).filter(Face.asset_id == asset_id).all()
        superseded_count = 0
        for face in faces:
            if face.origin_type not in ("superseded_by_upscale",):
                face.origin_type = "superseded_by_upscale"
                superseded_count += 1
        session.commit()

    if superseded_count:
        log.info(
            "Face dedupe rule: %d face crop(s) for asset %d marked superseded "
            "by upscale version %d",
            superseded_count, asset_id, version_id,
        )


def _generate_version_thumbnail(version_id: int, file_path: Path) -> None:
    from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
    from photofant.media.thumbnails import generate_thumbnail

    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    for size in (256, 512):
        try:
            thumb = generate_thumbnail(file_path, size)
            store_thumbnail(cache_path, version_id, size, thumb, "edit")
        except Exception:
            log.exception("Thumbnail failed for upscale version %d (size=%d)", version_id, size)


# ── Core upscale logic ────────────────────────────────────────────────────────

def _run_upscale(
    asset_id: int,
    model_id: str | None,
    params: dict[str, Any],
    status: JobStatus,
) -> None:
    from PIL import Image, ImageOps

    scale = int(params.get("scale", 4))

    resolved = _resolve_asset(asset_id)
    if resolved is None:
        raise ValueError(f"Asset {asset_id} not found or deleted")
    instance_id, person_id, source_path = resolved

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)

    upscaler_info = _resolve_upscaler_path(model_id)
    if upscaler_info is None:
        raise RuntimeError(
            "Kein aktiviertes Upscaler-Modell gefunden. "
            "Bitte ein SeedVR2-Modell in den Einstellungen aktivieren."
        )
    resolved_model_id, model_path = upscaler_info

    # Free VRAM before loading a new generative model
    generative_engine.unload()

    job_queue.update(status, progress=0.2, state=JobState.RUNNING)

    upscaler = SeedVR2Upscaler(model_path)
    upscaler.load()

    try:
        src = Path(source_path)
        with Image.open(src) as raw:
            img = ImageOps.exif_transpose(raw) or raw
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            img.load()

        job_queue.update(status, progress=0.4, state=JobState.RUNNING)

        upscaled = upscaler.upscale(img, scale=scale)
        width, height = upscaled.size

        job_queue.update(status, progress=0.7, state=JobState.RUNNING)

        # Write output file
        data_root = Path(__import__("photofant.config", fromlist=["get_data_root"]).get_data_root())
        with SessionLocal() as session:
            person = session.get(Person, person_id)
            if person is None:
                raise ValueError(f"Person {person_id} not found")
            person_dir = ensure_person_folder(data_root, person)

        edits_dir = person_dir / "edits"
        edits_dir.mkdir(parents=True, exist_ok=True)
        filename = f"upscale_{uuid.uuid4().hex[:12]}.jpg"
        edit_path = edits_dir / filename

        out_img = upscaled
        if out_img.mode in ("RGBA", "LA", "PA"):
            background = Image.new("RGB", out_img.size, (255, 255, 255))
            background.paste(out_img, mask=out_img.split()[-1])
            out_img = background
        elif out_img.mode != "RGB":
            out_img = out_img.convert("RGB")
        out_img.save(edit_path, format="JPEG", quality=95)

    finally:
        upscaler.unload()

    job_queue.update(status, progress=0.85, state=JobState.RUNNING)

    version_id = _create_upscale_version(
        instance_id=instance_id,
        person_id=person_id,
        edit_path=edit_path,
        width=width,
        height=height,
        model_id=resolved_model_id,
        scale=scale,
        params=params,
    )

    _apply_face_dedupe_upscale_rule(asset_id, version_id)
    _generate_version_thumbnail(version_id, edit_path)

    job_queue.update(status, progress=1.0, state=JobState.DONE)
    log.info("Upscale version %d created for asset %d (model=%s, scale=%dx)", version_id, asset_id, resolved_model_id, scale)


# ── Job entry point ───────────────────────────────────────────────────────────

async def run_upscale_job(
    status: JobStatus,
    asset_id: int,
    model_id: str | None,
    params: dict[str, Any],
) -> None:
    import asyncio
    await asyncio.to_thread(_run_upscale, asset_id, model_id, params, status)


async def enqueue_upscale(
    asset_id: int,
    model_id: str | None = None,
    params: dict[str, Any] | None = None,
) -> JobStatus:
    """Enqueue a single-asset upscale job."""
    resolved_params = params or {}
    return await job_queue.enqueue(
        kind=JobKind.UPSCALE,
        label=f"Upscale Bild #{asset_id}",
        coro_factory=lambda job_status: run_upscale_job(
            job_status, asset_id, model_id, resolved_params
        ),
    )
