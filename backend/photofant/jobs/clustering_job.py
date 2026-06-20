"""Clustering jobs — initial HDBSCAN + incremental face matching.

Initial clustering is triggered manually via API. Incremental matching runs
automatically after each face job to assign new faces to existing persons.
After assignment, person folders are materialized (files moved/copied).
"""
from __future__ import annotations

import asyncio
import logging

from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue

log = logging.getLogger(__name__)


def _run_initial_clustering() -> dict[str, int]:
    from photofant.clustering.engine import run_initial_clustering

    with SessionLocal() as session:
        cluster_stats = run_initial_clustering(session)

    from photofant.config import get_data_root
    from photofant.media.person_folders import materialize_clustering_results

    data_root = get_data_root()
    with SessionLocal() as session:
        mat_stats = materialize_clustering_results(session, data_root)

    return {**cluster_stats, **mat_stats}


async def run_clustering_job(status: JobStatus) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    result = await asyncio.to_thread(_run_initial_clustering)
    log.info("Clustering result: %s", result)
    job_queue.update(status, progress=1.0, state=JobState.DONE)


async def enqueue_clustering() -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.CLUSTERING,
        label="Personen-Clustering (HDBSCAN)",
        coro_factory=run_clustering_job,
    )


def run_incremental_match(face_id: int) -> None:
    """Match a single face against existing persons and assign or queue for review.

    On auto-assignment: materializes the person folder + moves face crop.
    """
    from photofant.clustering.engine import match_face_incremental
    from photofant.db.models import Face

    with SessionLocal() as session:
        result = match_face_incremental(session, face_id)

        face = session.get(Face, face_id)
        if face is None:
            return

        if result.band == "auto" and result.person_id is not None:
            face.person_id = result.person_id
            session.flush()

            from photofant.config import get_data_root
            from photofant.media.person_folders import materialize_assignment, move_face_crops_to_person

            data_root = get_data_root()
            materialize_assignment(session, face.asset_id, result.person_id, data_root)
            move_face_crops_to_person(session, face.asset_id, result.person_id, data_root)

            log.info(
                "Face %d auto-assigned to person %d (score=%.3f)",
                face_id, result.person_id, result.score,
            )

        elif result.band == "review" and result.person_id is not None:
            from datetime import UTC, datetime

            from photofant.db.models import ReviewItem

            existing = session.query(ReviewItem).filter(
                ReviewItem.type == "face_suggestion",
                ReviewItem.face_id == face_id,
                ReviewItem.resolved_at.is_(None),
            ).first()

            if existing is None:
                asset_id = face.asset_id or 0
                review_item = ReviewItem(
                    type="face_suggestion",
                    asset_a_id=asset_id,
                    asset_b_id=asset_id,
                    phash_distance=0,
                    face_id=face_id,
                    suggested_person_id=result.person_id,
                    score=result.score,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
                session.add(review_item)

            log.info(
                "Face %d → review suggestion for person %d (score=%.3f)",
                face_id, result.person_id, result.score,
            )

        session.commit()
