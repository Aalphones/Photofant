"""Caption job — runs captioner inference and persists a caption for one asset.

One job per asset; controlled by ProcessingLedger.caption_done (run exactly once).
Dispatches to the correct captioner based on the active model's caption_mode:
  - task_token  → Florence-2 (ONNX, lightweight, default)
  - instruct    → Qwen2.5-VL (transformers, heavy, VRAM-gated)
  - instruct_guided → JoyCaption (transformers, heavy, VRAM-gated)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from photofant.db.models import Asset, CaptionPreset, ModelRegistry, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.inference.caption_config import (
    CaptionMode,
    default_instruct_config,
    default_instruct_guided_config,
    default_task_token_config,
)
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


@dataclass
class _CaptionerInfo:
    model_db_id: int
    manifest_id: str
    caption_mode: str


# ---------------------------------------------------------------------------
# Active-captioner resolution
# ---------------------------------------------------------------------------


def _resolve_active_captioner() -> _CaptionerInfo | None:
    """Return info about the configured active captioner (from settings.active_captioner)."""
    from photofant.settings import load_settings

    settings = load_settings()
    preferred_id: str = settings.get("active_captioner", "florence-2-base")  # type: ignore[misc]

    with SessionLocal() as session:
        row = (
            session.query(ModelRegistry)
            .filter_by(manifest_id=preferred_id, enabled=True)
            .first()
        )
        if row is None:
            log.info(
                "Configured captioner %r not enabled or not registered — skipping caption",
                preferred_id,
            )
            return None
        return _CaptionerInfo(
            model_db_id=row.id,
            manifest_id=row.manifest_id,
            caption_mode=row.caption_mode or CaptionMode.TASK_TOKEN,
        )


# ---------------------------------------------------------------------------
# Preset resolution
# ---------------------------------------------------------------------------


def _resolve_default_preset(model_db_id: int | None, caption_mode: str) -> tuple[int | None, dict[str, Any]]:
    """Return (preset_id, config) for the active captioner.

    Priority:
    1. Model-specific is_default preset
    2. Global (model_id=NULL) is_default preset with compatible config structure
    3. Built-in default for the caption_mode
    """
    with SessionLocal() as session:
        query = session.query(CaptionPreset).filter_by(is_default=True)

        if model_db_id is not None:
            preset = query.filter_by(model_id=model_db_id).first()
            if preset is not None:
                return preset.id, dict(preset.config)

        # Global fallback — only use it if config structure matches the mode.
        global_presets = query.filter(CaptionPreset.model_id.is_(None)).all()
        for preset in global_presets:
            config = dict(preset.config)
            if _config_matches_mode(config, caption_mode):
                return preset.id, config

    return None, _built_in_default_config(caption_mode)


def _config_matches_mode(config: dict[str, Any], caption_mode: str) -> bool:
    """Heuristic: check if a config blob belongs to the given caption_mode."""
    if caption_mode == CaptionMode.TASK_TOKEN:
        return "task_token" in config
    if caption_mode == CaptionMode.INSTRUCT:
        return "system_prompt" in config
    if caption_mode == CaptionMode.INSTRUCT_GUIDED:
        return "caption_type" in config
    return False


def _built_in_default_config(caption_mode: str) -> dict[str, Any]:
    if caption_mode == CaptionMode.INSTRUCT:
        return default_instruct_config()
    if caption_mode == CaptionMode.INSTRUCT_GUIDED:
        return default_instruct_guided_config()
    return default_task_token_config()


def _resolve_preset_by_id(preset_id: int, caption_mode: str) -> tuple[int | None, dict[str, Any]]:
    """Return (preset_id, config) for a specific preset; falls back to default on miss."""
    with SessionLocal() as session:
        preset = session.get(CaptionPreset, preset_id)
        if preset is None:
            log.warning("Caption preset %d not found — falling back to default", preset_id)
            return _resolve_default_preset(None, caption_mode)
        return preset.id, dict(preset.config)


# ---------------------------------------------------------------------------
# Captioner dispatch
# ---------------------------------------------------------------------------


def _run_captioner(
    manifest_id: str,
    caption_mode: str,
    image: np.ndarray,
    preset_config: dict[str, Any],
) -> str:
    """Dispatch to the correct captioner implementation."""
    if caption_mode == CaptionMode.TASK_TOKEN:
        from photofant.inference.adapters.florence2 import resolve_florence_captioner
        captioner = resolve_florence_captioner()
        if captioner is None:
            log.info("Florence-2 not enabled — skipping caption")
            return ""
        return captioner.caption(image, preset_config)

    if caption_mode == CaptionMode.INSTRUCT:
        from photofant.inference.adapters.qwen_vl import resolve_qwen_captioner
        captioner = resolve_qwen_captioner()
        if captioner is None:
            log.info("Qwen2.5-VL not enabled — skipping caption")
            return ""
        return captioner.caption(image, preset_config)

    if caption_mode == CaptionMode.INSTRUCT_GUIDED:
        from photofant.inference.adapters.joycaption import resolve_joycaption
        captioner = resolve_joycaption()
        if captioner is None:
            log.info("JoyCaption not enabled — skipping caption")
            return ""
        return captioner.caption(image, preset_config)

    log.warning("Unknown caption_mode %r for model %s — skipping", caption_mode, manifest_id)
    return ""


# ---------------------------------------------------------------------------
# Core caption run
# ---------------------------------------------------------------------------


def _run_caption_with_preset(
    asset_id: int,
    override_preset_id: int | None = None,
    force: bool = False,
) -> None:
    """Blocking: resolve the active captioner, run inference, persist the caption."""
    from photofant.jobs.face_pipeline import face_pipeline

    try:
        _run_caption_with_preset_inner(asset_id, override_preset_id, force)
    finally:
        face_pipeline.signal(asset_id)


def _run_caption_with_preset_inner(
    asset_id: int,
    override_preset_id: int | None,
    force: bool,
) -> None:
    """Inner implementation; always called through _run_caption_with_preset."""
    from PIL import Image as PILImage

    from photofant.media.asset_paths import resolve_asset_path

    # Find the active captioner (heavy preferred over Florence).
    active_model = _resolve_active_captioner()
    if active_model is None:
        log.info("No captioner model enabled — skipping caption for asset %d", asset_id)
        return

    manifest_id: str = active_model.manifest_id
    caption_mode: str = active_model.caption_mode
    model_db_id: int = active_model.model_db_id

    # Preset resolution.
    if override_preset_id is not None:
        preset_id, preset_config = _resolve_preset_by_id(override_preset_id, caption_mode)
    else:
        preset_id, preset_config = _resolve_default_preset(model_db_id, caption_mode)

    # Respect manually edited captions — do not overwrite.
    with SessionLocal() as session:
        asset_check = session.get(Asset, asset_id)
        if asset_check is None:
            log.warning("Asset %d not found — skipping caption", asset_id)
            return
        if asset_check.caption_edited and not force:
            log.info("Asset %d has a manually edited caption — skipping captioner", asset_id)
            return

    asset_path = resolve_asset_path(asset_id)
    if asset_path is None:
        log.warning("Asset %d has no readable file — skipping caption", asset_id)
        return

    image = np.array(PILImage.open(asset_path).convert("RGB"), dtype=np.uint8)
    caption = _run_captioner(manifest_id, caption_mode, image, preset_config)

    if not caption:
        return

    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            log.warning("Asset %d not found — skipping caption persist", asset_id)
            return

        asset.caption = caption
        asset.captioner = manifest_id
        asset.caption_preset_id = preset_id
        if force:
            asset.caption_edited = False

        ledger = session.get(ProcessingLedger, asset.content_hash)
        if ledger is not None:
            ledger.caption_done = True

        session.commit()

    # Caption changed → keep smart-album membership in sync.
    from photofant.collections import engine

    with SessionLocal() as session:
        engine.evaluate_asset(session, asset_id)

    log.info("Captioned asset %d (%d chars, preset %s, model %s)", asset_id, len(caption), preset_id, manifest_id)


def _run_caption(asset_id: int) -> None:
    _run_caption_with_preset(asset_id)


async def run_caption_job(status: JobStatus, asset_id: int) -> None:
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_caption, asset_id)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_caption(asset_id: int) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.CAPTIONING,
        label=f"Caption: Asset {asset_id}",
        coro_factory=lambda job_status: run_caption_job(job_status, asset_id),
    )
