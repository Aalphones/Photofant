from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from sqlalchemy import select

from photofant.config import get_data_root
from photofant.db.models import Asset, AssetInstance, Face, Person, ProcessingLedger, Version
from photofant.db.session import SessionLocal
from photofant.jobs.import_job import steps_from_settings
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.maintenance.reconcile import (
    AcknowledgedMissingItem,
    IncompleteMetadataItem,
    InstanceRecord,
    MisassignedInstanceItem,
    OrphanedFaceItem,
    StrandedFaceItem,
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


def _gather_stranded_faces(data_root: Path) -> list[StrandedFaceItem]:
    """Faces assigned to a real person whose crop file isn't in that person's folder.

    Resolves each crop's folder back to a person; legacy `person_{id}/` and named
    folders both count as correct. Only a genuine mismatch — crop still under
    `_unknown/faces/`, or in another person's folder — is reported.
    """
    from photofant.media.person_folders import person_id_from_path

    items: list[StrandedFaceItem] = []
    with SessionLocal() as session:
        rows = session.execute(
            select(Face.id, Face.crop_path, Face.person_id, Person.name)
            .join(Person, Person.id == Face.person_id)
            .where(Person.is_unknown.is_(False))
        ).all()

        for face_id, crop_path, person_id, person_name in rows:
            folder_person_id = person_id_from_path(Path(crop_path), data_root, session)
            if folder_person_id == person_id:
                continue
            items.append(
                StrandedFaceItem(
                    face_id=face_id,
                    person_id=person_id,
                    person_name=person_name,
                    crop_path=crop_path,
                    detail=(
                        f"face.id={face_id} · gehört "
                        f"{person_name or f'Person {person_id}'} · Crop liegt im falschen Ordner"
                    ),
                )
            )

    return items


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


def _gather_incomplete_metadata() -> list[IncompleteMetadataItem]:
    """Active assets missing caption, tags, or CLIP embedding (steps enabled in settings
    only). One item per asset — an asset with multiple person instances would otherwise
    show up once per instance, but the gap doesn't depend on which person it's filed
    under, so only the first instance encountered is kept."""
    allowed = steps_from_settings()
    with SessionLocal() as session:
        rows = session.execute(
            select(
                Asset.id,
                AssetInstance.path,
                Person.name,
                ProcessingLedger.tags_done,
                ProcessingLedger.caption_done,
                ProcessingLedger.embedding_done,
            )
            .join(AssetInstance, AssetInstance.asset_id == Asset.id)
            .join(Person, Person.id == AssetInstance.person_id)
            .outerjoin(ProcessingLedger, ProcessingLedger.content_hash == Asset.content_hash)
            .where(AssetInstance.deleted_at.is_(None))
            .where(AssetInstance.missing_at.is_(None))
            .order_by(Asset.id, AssetInstance.id)
        ).all()

    items: list[IncompleteMetadataItem] = []
    seen: set[int] = set()
    for asset_id, path, person_name, tags_done, caption_done, embedding_done in rows:
        if asset_id in seen:
            continue
        seen.add(asset_id)
        missing: list[str] = []
        if allowed.tags and not tags_done:
            missing.append("tags")
        if allowed.caption and not caption_done:
            missing.append("caption")
        if allowed.embedding and not embedding_done:
            missing.append("embedding")
        if not missing:
            continue
        items.append(
            IncompleteMetadataItem(
                asset_id=asset_id,
                path=path,
                person_name=person_name,
                missing=missing,
                detail=f"asset.id={asset_id} · fehlt: {', '.join(missing)}",
            )
        )
    return items


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
    report.stranded_faces = _gather_stranded_faces(data_root)
    report.incomplete_metadata = _gather_incomplete_metadata()

    with SessionLocal() as session:
        persist_report(session, report)

    log.info(
        "Reconcile done: %d orphaned, %d missing, %d drift, %d orphaned faces, "
        "%d misassigned, %d acknowledged-missing, %d orphaned edits, %d stranded faces, "
        "%d incomplete metadata",
        len(report.orphaned_files),
        len(report.missing_files),
        len(report.path_drift),
        len(report.orphaned_faces),
        len(report.misassigned_instances),
        len(report.acknowledged_missing),
        len(report.orphaned_edits),
        len(report.stranded_faces),
        len(report.incomplete_metadata),
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
