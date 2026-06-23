"""Flux-Edit job — GPU-based img2img via FluxImg2ImgPipeline (P9 Phase 4).

POST /api/assets/{id}/flux-edit  →  enqueues this job.

Flow:
  1. Resolve asset → get source file path.
  2. Load Flux components from the registry (editor role, FluxImg2ImgPipeline).
  3. Run img2img with prompt + params; save result to person's edits/ folder.
  4. Create Version(type="flux_edit", is_current=True) with seed in params.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from photofant.db.models import AssetInstance, Person, Version
from photofant.db.session import SessionLocal
from photofant.inference.generative_engine import (
    GenerativeAvailability,
    check_generative_available,
    generative_engine,
)
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.media.person_folders import ensure_person_folder

log = logging.getLogger(__name__)

DEFAULT_STRENGTH: float = 0.65
DEFAULT_STEPS: int = 20
DEFAULT_GUIDANCE: float = 7.5


def _resolve_editor_model() -> tuple[str, dict[str, str] | None, str | None]:
    """Return (manifest_id, components, path) for the first enabled editor model."""
    from photofant.db.models import ModelRegistry

    with SessionLocal() as session:
        row = (
            session.query(ModelRegistry)
            .filter_by(role="editor", enabled=True)
            .first()
        )
        if row is None:
            raise RuntimeError(
                "Kein aktiviertes Editor-Modell gefunden. "
                "Bitte ein Flux-Modell in den Einstellungen aktivieren."
            )
        return (row.manifest_id, row.components, row.path)


def _resolve_asset(asset_id: int) -> tuple[int, int, str]:
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
        raise ValueError(f"Asset {asset_id} not found or deleted")
    return (int(row[0]), int(row[1]), str(row[2]))


def _create_flux_edit_version(
    instance_id: int,
    person_id: int,
    edit_path: Path,
    width: int,
    height: int,
    model_id: str,
    prompt: str,
    params: dict[str, Any],
    seed: int,
) -> int:
    """Write flux_edit Version row; return version.id."""
    from photofant.config import get_data_root

    data_root = Path(get_data_root())
    with SessionLocal() as session:
        person = session.get(Person, person_id)
        if person is None:
            raise ValueError(f"Person {person_id} not found")
        person_dir = ensure_person_folder(data_root, person)

    edits_dir = person_dir / "edits"
    edits_dir.mkdir(parents=True, exist_ok=True)

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
            type="flux_edit",
            parent_id=None,
            path=str(edit_path.resolve()),
            is_current=True,
            params={
                "model_id": model_id,
                "prompt": prompt,
                "seed": seed,
                "width": width,
                "height": height,
                **{k: v for k, v in params.items() if k not in ("prompt", "template_id")},
            },
            created_at=datetime.now(UTC),
        )
        session.add(version)
        session.commit()
        return int(version.id)


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
            log.exception("Thumbnail failed for flux_edit version %d (size=%d)", version_id, size)


def _run_flux_edit(
    asset_id: int,
    prompt: str,
    params: dict[str, Any],
    status: JobStatus,
) -> None:
    import torch
    from PIL import Image, ImageOps

    strength = float(params.get("strength", DEFAULT_STRENGTH))
    steps = int(params.get("steps", DEFAULT_STEPS))
    guidance = float(params.get("guidance", DEFAULT_GUIDANCE))
    seed_input = int(params.get("seed", -1))

    instance_id, person_id, source_path = _resolve_asset(asset_id)
    job_queue.update(status, progress=0.05, state=JobState.RUNNING)

    manifest_id, components, model_path = _resolve_editor_model()
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)

    # Free VRAM then load pipeline
    generative_engine.unload()

    pipeline = generative_engine.load_pipeline(
        model_id=manifest_id,
        pipeline_class_name="FluxImg2ImgPipeline",
        model_path=model_path,
        components=components,
        torch_dtype="bfloat16",
    )
    job_queue.update(status, progress=0.3, state=JobState.RUNNING)

    # Load source image
    src = Path(source_path)
    with Image.open(src) as raw:
        img = ImageOps.exif_transpose(raw) or raw
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.load()

    # Determine seed
    if seed_input < 0:
        seed = torch.randint(0, 2**32 - 1, (1,)).item()
    else:
        seed = seed_input
    generator = torch.Generator(device="cuda").manual_seed(int(seed))

    job_queue.update(status, progress=0.4, state=JobState.RUNNING)

    result = pipeline(
        prompt=prompt,
        image=img,
        strength=strength,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=generator,
    )
    out_img = result.images[0]
    width, height = out_img.size

    job_queue.update(status, progress=0.75, state=JobState.RUNNING)

    # Write output
    from photofant.config import get_data_root
    data_root = Path(get_data_root())
    with SessionLocal() as session:
        person = session.get(Person, person_id)
        if person is None:
            raise ValueError(f"Person {person_id} not found")
        person_dir = ensure_person_folder(data_root, person)
    edits_dir = person_dir / "edits"
    edits_dir.mkdir(parents=True, exist_ok=True)

    filename = f"flux_edit_{uuid.uuid4().hex[:12]}.jpg"
    edit_path = edits_dir / filename

    save_img = out_img
    if save_img.mode in ("RGBA", "LA", "PA"):
        background = Image.new("RGB", save_img.size, (255, 255, 255))
        background.paste(save_img, mask=save_img.split()[-1])
        save_img = background
    elif save_img.mode != "RGB":
        save_img = save_img.convert("RGB")
    save_img.save(edit_path, format="JPEG", quality=95)

    job_queue.update(status, progress=0.85, state=JobState.RUNNING)

    version_id = _create_flux_edit_version(
        instance_id=instance_id,
        person_id=person_id,
        edit_path=edit_path,
        width=width,
        height=height,
        model_id=manifest_id,
        prompt=prompt,
        params=params,
        seed=int(seed),
    )
    _generate_version_thumbnail(version_id, edit_path)

    job_queue.update(status, progress=1.0, state=JobState.DONE)
    log.info(
        "Flux-Edit version %d created for asset %d (model=%s, seed=%d)",
        version_id, asset_id, manifest_id, seed,
    )


async def run_flux_edit_job(
    status: JobStatus,
    asset_id: int,
    prompt: str,
    params: dict[str, Any],
) -> None:
    import asyncio
    await asyncio.to_thread(_run_flux_edit, asset_id, prompt, params, status)


async def enqueue_flux_edit(
    asset_id: int,
    prompt: str,
    params: dict[str, Any] | None = None,
) -> JobStatus:
    resolved_params = params or {}
    return await job_queue.enqueue(
        kind=JobKind.FLUX_EDIT,
        label=f"Flux-Edit Bild #{asset_id}",
        coro_factory=lambda job_status: run_flux_edit_job(
            job_status, asset_id, prompt, resolved_params
        ),
    )
