"""Tagging job — runs WD14 inference and persists tags for a single asset.

One job per asset; controlled by ProcessingLedger.tags_done (run exactly once).
"""
from __future__ import annotations

import logging

import numpy as np

from photofant.db.models import Asset, AssetTag, ProcessingLedger, Tag
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


def _run_tagging(asset_id: int, asset_path: str) -> None:
    """Blocking: run WD14 inference + persist tags for one asset."""
    from PIL import Image as PILImage

    from photofant.inference.adapters.wd14 import resolve_wd14_tagger
    from photofant.settings import load_settings

    threshold = load_settings()["tagging_threshold"]
    tagger = resolve_wd14_tagger(threshold=threshold)
    if tagger is None:
        log.info("WD14 not enabled — skipping tagging for asset %d", asset_id)
        return

    image = np.array(PILImage.open(asset_path).convert("RGB"), dtype=np.uint8)
    tag_scores = tagger.tag(image)

    with SessionLocal() as session:
        asset = session.get(Asset, asset_id)
        if asset is None:
            log.warning("Asset %d not found — skipping tag persist", asset_id)
            return

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


async def run_tagging_job(status: JobStatus, asset_id: int, asset_path: str) -> None:
    import asyncio

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_tagging, asset_id, asset_path)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_tagging(asset_id: int, asset_path: str) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.TAGGING,
        label=f"Tagging: Asset {asset_id}",
        coro_factory=lambda job_status: run_tagging_job(job_status, asset_id, asset_path),
    )
