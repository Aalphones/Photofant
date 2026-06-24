from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from sqlalchemy import select

from photofant.config import get_data_root
from photofant.db.models import Asset, AssetInstance, Person
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.maintenance.reconcile import InstanceRecord, classify_reconcile
from photofant.maintenance.store import persist_report
from photofant.media.meta import SUPPORTED_EXTENSIONS

log = logging.getLogger(__name__)

_PHOTOFANT_DIRNAME = ".photofant"

# Subdirectory names that are NOT tracked by asset_instance and must be
# excluded from the reconcile walk to avoid false orphan reports.
# - faces/  → tracked via Face.crop_path (managed by face_job + face_folder_scan_job)
# - edits/  → tracked via Version.path (managed by edit pipeline)
_EXCLUDED_SUBDIRS = {"faces", "edits"}


def _gather_active_instances() -> list[InstanceRecord]:
    """Active rows (not soft-deleted, not already acknowledged-missing)."""
    with SessionLocal() as session:
        rows = session.execute(
            select(
                AssetInstance.id,
                AssetInstance.asset_id,
                Asset.content_hash,
                Asset.file_size,
                AssetInstance.path,
                Person.name,
            )
            .join(Asset, Asset.id == AssetInstance.asset_id)
            .join(Person, Person.id == AssetInstance.person_id)
            .where(AssetInstance.deleted_at.is_(None))
            .where(AssetInstance.missing_at.is_(None))
        ).all()

    return [
        InstanceRecord(
            instance_id=row[0],
            asset_id=row[1],
            content_hash=row[2],
            file_size=row[3],
            path=row[4],
            person_name=row[5],
        )
        for row in rows
    ]


def _walk_data_root(data_root: Path) -> list[Path]:
    """All supported image files under data_root, excluding managed subtrees.

    Pruned directories:
      .photofant/ — trash, backups, cache
      faces/      — face crops tracked via Face.crop_path, not AssetInstance
      edits/      — edited versions tracked via Version.path, not AssetInstance
    """
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(data_root):
        if _PHOTOFANT_DIRNAME in dirnames:
            dirnames.remove(_PHOTOFANT_DIRNAME)
        for excluded in _EXCLUDED_SUBDIRS:
            if excluded in dirnames:
                dirnames.remove(excluded)
        for filename in filenames:
            if Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS:
                found.append(Path(dirpath) / filename)
    return found


def _run_reconcile() -> int:
    data_root = get_data_root()
    active = _gather_active_instances()
    fs_paths = _walk_data_root(data_root)
    report = classify_reconcile(active, fs_paths)

    with SessionLocal() as session:
        persist_report(session, report)

    log.info(
        "Reconcile done: %d orphaned, %d missing, %d drift",
        len(report.orphaned_files),
        len(report.missing_files),
        len(report.path_drift),
    )
    return report.total


async def run_reconcile_job(status: JobStatus) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_reconcile)


async def enqueue_reconcile() -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.RECONCILE,
        label="FS↔DB-Abgleich",
        coro_factory=run_reconcile_job,
    )
