"""Bulk-assign job — move a selection of assets to a target person.

POST /api/persons/{person_id}/bulk-assign  →  { asset_ids }

Reuses `materialize_assignment` / `move_face_crops_to_person` /
`prune_orphaned_instances` from person_folders.py instead of hand-rolling file
moves — those already handle the (asset_id, person_id) unique-constraint
collision a naive move would hit on a rerun, plus favourites/edits subfolder
placement (ADR-013). Per-asset errors are collected and logged; the job never
aborts early.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select

from photofant.db.models import Face, Person
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.media.person_folders import (
    materialize_assignment,
    move_face_crops_to_person,
    prune_orphaned_instances,
)

log = logging.getLogger(__name__)


def _get_unknown_person_id() -> int | None:
    with SessionLocal() as session:
        person = session.scalar(select(Person).where(Person.is_unknown.is_(True)))
        return person.id if person is not None else None


def _reassign_unknown_faces(session, asset_id: int, target_person_id: int, unknown_person_id: int) -> None:
    """Best-scoring _unknown face on this asset moves to the target person; the rest stay _unknown."""
    faces = session.scalars(
        select(Face).where(Face.asset_id == asset_id, Face.person_id == unknown_person_id)
    ).all()
    if not faces:
        return
    best = max(faces, key=lambda face: face.score if face.score is not None else -1.0)
    best.person_id = target_person_id
    session.flush()


def _assign_one_asset(
    asset_id: int,
    target_person_id: int,
    data_root: Path,
    unknown_person_id: int | None,
) -> bool:
    with SessionLocal() as session:
        instance = materialize_assignment(session, asset_id, target_person_id, data_root, fixed=True)
        if instance is None:
            session.rollback()
            return False

        if unknown_person_id is not None:
            _reassign_unknown_faces(session, asset_id, target_person_id, unknown_person_id)
            move_face_crops_to_person(session, asset_id, target_person_id, data_root)

        prune_orphaned_instances(session, asset_id, data_root)

        from photofant.jobs.recommendation_job import invalidate_recommendations

        invalidate_recommendations(session, [asset_id])

        session.commit()
        return True


async def run_bulk_assign_person_job(status: JobStatus, asset_ids: list[int], person_id: int) -> None:
    from photofant.config import get_data_root

    data_root = get_data_root()
    unknown_id = await asyncio.to_thread(_get_unknown_person_id)
    total = max(len(asset_ids), 1)
    succeeded: list[int] = []
    errors: list[str] = []

    job_queue.update(status, progress=0.0, state=JobState.RUNNING)

    for index, asset_id in enumerate(asset_ids):
        try:
            moved = await asyncio.to_thread(_assign_one_asset, asset_id, person_id, data_root, unknown_id)
            if moved:
                succeeded.append(asset_id)
            else:
                errors.append(f"Asset {asset_id}: Datei fehlt oder Person ungültig")
        except Exception as exc:
            errors.append(f"Asset {asset_id}: {exc}")
            log.exception("Bulk-assign failed for asset %d", asset_id)
        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)

    if succeeded:
        from photofant.jobs.collections_job import enqueue_reevaluate_assets
        await enqueue_reevaluate_assets(succeeded)

    if errors:
        log.warning("Bulk-assign finished with %d error(s):\n%s", len(errors), "\n".join(errors))
    log.info("Bulk-assign done: %d/%d asset(s) -> person %d", len(succeeded), len(asset_ids), person_id)


async def enqueue_bulk_assign_person(asset_ids: list[int], person_id: int) -> JobStatus:
    count = len(asset_ids)
    return await job_queue.enqueue(
        kind=JobKind.BULK_ASSIGN,
        label=f"{count} Bild(er) zuweisen",
        coro_factory=lambda job_status: run_bulk_assign_person_job(job_status, asset_ids, person_id),
    )
