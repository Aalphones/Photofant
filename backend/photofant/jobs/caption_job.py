"""Caption job — runs Florence-2 inference and persists a caption for one asset.

One job per asset; controlled by ProcessingLedger.caption_done (run exactly once).
The active captioner's default preset supplies the task token / generation knobs;
its id is stamped onto the asset for provenance (Konzept §12.6).
"""
from __future__ import annotations

import logging

import numpy as np

from photofant.db.models import Asset, CaptionPreset, ModelRegistry, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.inference.caption_config import default_task_token_config
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)

_CAPTIONER_MANIFEST_ID = "florence-2-base"


def _resolve_default_preset() -> tuple[int | None, dict]:  # type: ignore[type-arg]
    """Return (preset_id, config) for the captioner's default preset.

    Prefers a preset bound to the active captioner, then a model-agnostic default,
    then the built-in task_token defaults (preset_id = None).
    """
    with SessionLocal() as session:
        model = (
            session.query(ModelRegistry)
            .filter_by(manifest_id=_CAPTIONER_MANIFEST_ID, enabled=True)
            .first()
        )
        model_id = model.id if model is not None else None

        query = session.query(CaptionPreset).filter_by(is_default=True)
        preset = None
        if model_id is not None:
            preset = query.filter_by(model_id=model_id).first()
        if preset is None:
            preset = query.filter(CaptionPreset.model_id.is_(None)).first()

        if preset is not None:
            return preset.id, dict(preset.config)

    return None, default_task_token_config()


def _resolve_preset_by_id(preset_id: int) -> tuple[int | None, dict]:  # type: ignore[type-arg]
    """Return (preset_id, config) for a specific preset; falls back to default if not found."""
    with SessionLocal() as session:
        preset = session.get(CaptionPreset, preset_id)
        if preset is None:
            log.warning("Caption preset %d not found — falling back to default", preset_id)
            return _resolve_default_preset()
        return preset.id, dict(preset.config)


def _run_caption_with_preset(
    asset_id: int, asset_path: str, override_preset_id: int | None = None
) -> None:
    """Blocking: run Florence-2 inference + persist the caption for one asset.

    If override_preset_id is given, that preset is used instead of the default.
    """
    from PIL import Image as PILImage

    from photofant.inference.adapters.florence2 import resolve_florence_captioner

    captioner = resolve_florence_captioner()
    if captioner is None:
        log.info("Florence-2 not enabled — skipping caption for asset %d", asset_id)
        return

    if override_preset_id is not None:
        preset_id, preset_config = _resolve_preset_by_id(override_preset_id)
    else:
        preset_id, preset_config = _resolve_default_preset()

    # Respect manually edited captions — do not overwrite
    with SessionLocal() as session:
        asset_check = session.get(Asset, asset_id)
        if asset_check is None:
            log.warning("Asset %d not found — skipping caption", asset_id)
            return
        if asset_check.caption_edited:
            log.info("Asset %d has a manually edited caption — skipping captioner", asset_id)
            return

    image = np.array(PILImage.open(asset_path).convert("RGB"), dtype=np.uint8)
    caption = captioner.caption(image, preset_config)

    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            log.warning("Asset %d not found — skipping caption persist", asset_id)
            return

        asset.caption = caption
        asset.captioner = _CAPTIONER_MANIFEST_ID
        asset.caption_preset_id = preset_id

        ledger = session.get(ProcessingLedger, asset.content_hash)
        if ledger is not None:
            ledger.caption_done = True

        session.commit()

    log.info("Captioned asset %d (%d chars, preset %s)", asset_id, len(caption), preset_id)


def _run_caption(asset_id: int, asset_path: str) -> None:
    """Blocking: run Florence-2 inference + persist the caption for one asset."""
    _run_caption_with_preset(asset_id, asset_path)


async def run_caption_job(status: JobStatus, asset_id: int, asset_path: str) -> None:
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_caption, asset_id, asset_path)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_caption(asset_id: int, asset_path: str) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.CAPTIONING,
        label=f"Caption: Asset {asset_id}",
        coro_factory=lambda job_status: run_caption_job(job_status, asset_id, asset_path),
    )
