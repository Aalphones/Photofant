from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from sqlalchemy import select

from photofant.config import get_data_root
from photofant.db.models import Asset, AssetInstance, Face, Person, Version
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.maintenance.reconcile import (
    AcknowledgedMissingItem,
    InstanceRecord,
    MisassignedInstanceItem,
    OrphanedFaceItem,
    classify_orphaned_edits,
    classify_reconcile,
    norm_path,
)
from photofant.maintenance.store import persist_report
from photofant.media.meta import SUPPORTED_EXTENSIONS

log = logging.getLogger(__name__)

_PHOTOFANT_DIRNAME = ".photofant"

# Subdirectory names that are NOT tracked by asset_instance and must be
# excluded from the main reconcile walk to avoid false orphan reports.
# - faces/  → tracked via Face.crop_path (managed by face_job + face_folder_scan_job)
# - edits/  → tracked via Version.path (managed by edit pipeline); reconciled
#             separately below (_walk_edits_dirs + classify_orphaned_edits) since
#             Version rows carry no content_hash for drift rehashing.
_EXCLUDED_SUBDIRS = {"faces", "edits"}
_EDITS_DIRNAME = "edits"


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


def _walk_edits_dirs(data_root: Path) -> list[Path]:
    """All supported image files sitting directly in an `edits/` folder.

    Mirrors `_walk_data_root`'s pruning (skips `.photofant/`) but only collects
    files whose immediate parent directory is named `edits` — that's where the
    edit pipeline writes rendered versions (`personX/edits/`, `_unknown/edits/`).
    """
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(data_root):
        if _PHOTOFANT_DIRNAME in dirnames:
            dirnames.remove(_PHOTOFANT_DIRNAME)
        if Path(dirpath).name != _EDITS_DIRNAME:
            continue
        for filename in filenames:
            if Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS:
                found.append(Path(dirpath) / filename)
    return found


def _gather_active_version_paths() -> set[str]:
    """Normalised paths of every `version` row — the "already linked" set for edits."""
    with SessionLocal() as session:
        paths = session.execute(select(Version.path)).scalars().all()
    return {norm_path(path) for path in paths}


def _gather_orphaned_faces() -> list[OrphanedFaceItem]:
    """Face rows with a set asset_id whose parent Asset no longer exists."""
    with SessionLocal() as session:
        rows = session.execute(
            select(
                Face.id,
                Face.asset_id,
                Face.crop_path,
                Person.name,
            )
            .outerjoin(Asset, Asset.id == Face.asset_id)
            .outerjoin(Person, Person.id == Face.person_id)
            .where(Face.asset_id.is_not(None))
            .where(Asset.id.is_(None))
        ).all()

    return [
        OrphanedFaceItem(
            face_id=row[0],
            asset_id=row[1],
            crop_path=row[2],
            person_name=row[3],
            detail=f"face.id={row[0]} · parent asset.id={row[1]} nicht mehr vorhanden",
        )
        for row in rows
    ]


def _gather_misassigned_instances() -> list[MisassignedInstanceItem]:
    """Active real-person instances the asset's faces no longer back.

    The asset has at least one face, but none belongs to the instance's person —
    a stale wrong assignment. Face-less assets are excluded (a deliberate
    person assignment without a face is left alone), as are `_unknown` rows.
    """
    with SessionLocal() as session:
        asset_has_face = (
            select(Face.id)
            .where(Face.asset_id == AssetInstance.asset_id)
            .exists()
        )
        person_has_face = (
            select(Face.id)
            .where(
                Face.asset_id == AssetInstance.asset_id,
                Face.person_id == AssetInstance.person_id,
            )
            .exists()
        )
        rows = session.execute(
            select(
                AssetInstance.id,
                AssetInstance.asset_id,
                AssetInstance.path,
                Person.name,
            )
            .join(Person, Person.id == AssetInstance.person_id)
            .where(AssetInstance.deleted_at.is_(None))
            .where(Person.is_unknown.is_(False))
            .where(asset_has_face)
            .where(~person_has_face)
        ).all()

    return [
        MisassignedInstanceItem(
            instance_id=row[0],
            asset_id=row[1],
            path=row[2],
            person_name=row[3],
            detail=f"asset.id={row[1]} · {row[3] or '?'} ohne Gesicht auf diesem Bild",
        )
        for row in rows
    ]


def _gather_acknowledged_missing() -> list[AcknowledgedMissingItem]:
    """AssetInstances already marked missing but not yet purged (missing_at IS NOT NULL)."""
    with SessionLocal() as session:
        rows = session.execute(
            select(
                AssetInstance.id,
                AssetInstance.asset_id,
                AssetInstance.path,
                AssetInstance.missing_at,
                Person.name,
            )
            .join(Asset, Asset.id == AssetInstance.asset_id)
            .join(Person, Person.id == AssetInstance.person_id)
            .where(AssetInstance.missing_at.is_not(None))
            .where(AssetInstance.deleted_at.is_(None))
        ).all()

    return [
        AcknowledgedMissingItem(
            instance_id=row[0],
            asset_id=row[1],
            path=row[2],
            missing_at=str(row[3]),
            person_name=row[4],
            detail=f"asset.id={row[1]} · als fehlend markiert am {str(row[3])[:10]}",
        )
        for row in rows
    ]


def _run_reconcile() -> int:
    data_root = get_data_root()
    active = _gather_active_instances()
    fs_paths = _walk_data_root(data_root)
    report = classify_reconcile(active, fs_paths)
    report.orphaned_faces = _gather_orphaned_faces()
    report.misassigned_instances = _gather_misassigned_instances()
    report.acknowledged_missing = _gather_acknowledged_missing()
    report.orphaned_edits = classify_orphaned_edits(
        _walk_edits_dirs(data_root), _gather_active_version_paths()
    )

    with SessionLocal() as session:
        persist_report(session, report)

    log.info(
        "Reconcile done: %d orphaned, %d missing, %d drift, %d orphaned faces, "
        "%d misassigned, %d acknowledged-missing, %d orphaned edits",
        len(report.orphaned_files),
        len(report.missing_files),
        len(report.path_drift),
        len(report.orphaned_faces),
        len(report.misassigned_instances),
        len(report.acknowledged_missing),
        len(report.orphaned_edits),
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
