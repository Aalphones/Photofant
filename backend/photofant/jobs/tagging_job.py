"""Tagging job — runs WD14 inference and persists tags for a single asset.

One job per asset; controlled by ProcessingLedger.tags_done (run exactly once).
"""
from __future__ import annotations

import logging

import numpy as np

from photofant.db.models import Asset, AssetTag, ProcessingLedger, Tag
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.worker.signals import emit_pipeline_signal

log = logging.getLogger(__name__)


def _run_tagging(asset_id: int) -> None:
    """Blocking: run WD14 inference + persist tags for one asset.

    The follow-up signals fire in `finally`: face detection and classification
    wait for this step, and a tagging failure must not strand them forever.
    """
    try:
        _run_tagging_inner(asset_id)
    finally:
        emit_pipeline_signal("face", asset_id)
        emit_pipeline_signal("classification", asset_id)


def _run_tagging_inner(asset_id: int) -> None:
    """Inner implementation; always called through `_run_tagging`."""
    from PIL import Image as PILImage

    from photofant.inference.adapters.wd14 import resolve_wd14_tagger
    from photofant.media.asset_paths import resolve_asset_path
    from photofant.settings import load_settings

    settings = load_settings()
    threshold = settings["min_probability"]
    max_tags = settings["max_tags"]
    tagger = resolve_wd14_tagger(threshold=threshold)
    if tagger is None:
        log.info("WD14 not enabled — skipping tagging for asset %d", asset_id)
        return

    asset_path = resolve_asset_path(asset_id)
    if asset_path is None:
        log.warning("Asset %d has no readable file — skipping tagging", asset_id)
        return

    with PILImage.open(asset_path) as raw:
        image = np.array(raw.convert("RGB"), dtype=np.uint8)
    tag_scores = tagger.tag(image)
    tag_scores = tag_scores[:max_tags]  # tagger already sorts by score desc

    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            log.warning("Asset %d not found — skipping tag persist", asset_id)
            return

        # Clear stale auto-tags so rerun produces a clean result set.
        # Manually-removed entries (manually_removed=True) are intentionally kept
        # to prevent the tagger from re-adding explicitly rejected tags.
        session.query(AssetTag).filter(
            AssetTag.asset_id == asset_id,
            AssetTag.kind == "auto",
            AssetTag.manually_removed.is_(False),
        ).delete(synchronize_session=False)
        session.flush()

        for tag_score in tag_scores:
            normalized_name = tag_score.name.lower()
            existing_tag = session.query(Tag).filter_by(name=normalized_name).first()
            if existing_tag is None:
                new_tag = Tag(name=normalized_name)
                session.add(new_tag)
                session.flush()
                tag_id = new_tag.id
            else:
                tag_id = existing_tag.id

            existing_asset_tag = (
                session.query(AssetTag)
                .filter_by(asset_id=asset_id, tag_id=tag_id)
                .first()
            )
            if existing_asset_tag is None:
                session.add(AssetTag(
                    asset_id=asset_id,
                    tag_id=tag_id,
                    kind="auto",
                    score=tag_score.score,
                ))
            elif existing_asset_tag.manually_removed:
                pass  # user explicitly removed this tag — don't re-add
            elif existing_asset_tag.kind == "manual":
                pass  # user manually added this tag — don't overwrite
            else:
                existing_asset_tag.score = tag_score.score

        asset.tagger = "wd-swinv2-v3"

        ledger = session.get(ProcessingLedger, asset.content_hash)
        if ledger is not None:
            ledger.tags_done = True

        session.commit()

    # Tags changed → keep smart-album membership in sync (covers initial import + rerun)
    from photofant.collections import engine

    with SessionLocal() as session:
        engine.evaluate_asset(session, asset_id)

    log.info("Tagged asset %d: %d tag(s) persisted", asset_id, len(tag_scores))


async def run_tagging_job(status: JobStatus, asset_id: int) -> None:
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_tagging, asset_id)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_tagging(asset_id: int) -> JobStatus:
    return await job_queue.enqueue_remote(
        kind=JobKind.TAGGING,
        label=f"Tagging: Asset {asset_id}",
        payload={"asset_id": asset_id},
    )
