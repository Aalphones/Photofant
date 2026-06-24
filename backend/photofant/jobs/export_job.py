"""Export jobs — copy favourites or collection items to a local export folder.

All jobs write into ``<data_root>/_export/<timestamp>_<kind>/`` so the user can
find them in one place. File-system first, no DB writes needed.
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from photofant.config import get_data_root
from photofant.db.models import Asset, AssetInstance, CollectionItem, Person
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobStatus, job_queue

log = logging.getLogger(__name__)

_EXPORT_ROOT = "_export"


def _export_dir(kind: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
    directory = get_data_root() / _EXPORT_ROOT / f"{timestamp}_{kind}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _safe_name(name: str) -> str:
    """Sanitize a person name for use as a directory name."""
    return re.sub(r"[^\w\-]", "_", name).strip("_") or "unbekannt"


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(src, dest)
    else:
        stem = dest.stem
        suffix = dest.suffix
        counter = 1
        candidate = dest.with_name(f"{stem}_{counter}{suffix}")
        while candidate.exists():
            counter += 1
            candidate = dest.with_name(f"{stem}_{counter}{suffix}")
        shutil.copy2(src, candidate)


def _base_favourite_query(session: Session) -> list[tuple[AssetInstance, Asset, Person | None]]:
    rows = (
        session.query(AssetInstance, Asset, Person)
        .join(Asset, Asset.id == AssetInstance.asset_id)
        .outerjoin(Person, Person.id == AssetInstance.person_id)
        .filter(AssetInstance.favourite.is_(True))
        .filter(AssetInstance.deleted_at.is_(None))
        .all()
    )
    return rows


# ---------------------------------------------------------------------------
# Job: export by current filter (favourite=True + optional extra filters)
# ---------------------------------------------------------------------------

def _run_export_filter(
    dest: Path,
    source_filter: list[str] | None,
    quality_min: float | None,
    tag_ids: list[int] | None,
    person_id: int | None,
    include_versions: bool = False,
) -> int:
    from sqlalchemy import or_

    from photofant.db.models import AssetTag, Tag

    with SessionLocal() as session:
        query = (
            session.query(AssetInstance, Asset)
            .join(Asset, Asset.id == AssetInstance.asset_id)
            .filter(AssetInstance.favourite.is_(True))
            .filter(AssetInstance.deleted_at.is_(None))
        )
        if source_filter:
            query = query.filter(Asset.source.in_(source_filter))
        if quality_min and quality_min > 0:
            query = query.filter(Asset.quality_score >= quality_min)
        if person_id is not None:
            query = query.filter(AssetInstance.person_id == person_id)
        for tag_id in (tag_ids or []):
            alias_ids_sub = session.query(Tag.id).filter(Tag.alias_of == tag_id).subquery()
            tag_sub = (
                session.query(AssetTag.asset_id)
                .filter(
                    AssetTag.manually_removed.is_(False),
                    or_(AssetTag.tag_id == tag_id, AssetTag.tag_id.in_(alias_ids_sub)),
                )
                .subquery()
            )
            query = query.filter(Asset.id.in_(tag_sub))

        rows = query.all()
        matched_asset_ids = {asset.id for _, asset in rows}

        # Collect sibling asset IDs (derivatives / originals in the same tree)
        extra_paths: list[Path] = []
        if include_versions and matched_asset_ids:
            root_ids: set[int] = set()
            for _, asset in rows:
                root_ids.add(asset.original_id if asset.original_id else asset.id)
            version_rows = (
                session.query(AssetInstance.path)
                .join(Asset, Asset.id == AssetInstance.asset_id)
                .filter(AssetInstance.deleted_at.is_(None))
                .filter(
                    or_(
                        Asset.id.in_(root_ids),
                        Asset.original_id.in_(root_ids),
                    )
                )
                .filter(Asset.id.notin_(matched_asset_ids))
                .all()
            )
            extra_paths = [Path(row[0]) for row in version_rows]

        count = 0
        seen_paths: set[str] = set()
        for instance, _asset in rows:
            src = Path(instance.path)
            if src.exists() and str(src) not in seen_paths:
                _copy_file(src, dest / src.name)
                seen_paths.add(str(src))
                count += 1
        for src in extra_paths:
            if src.exists() and str(src) not in seen_paths:
                _copy_file(src, dest / "ableitungen" / src.name)
                seen_paths.add(str(src))
                count += 1
        return count


async def run_export_filter_job(
    status: JobStatus,
    source_filter: list[str] | None,
    quality_min: float | None,
    tag_ids: list[int] | None,
    person_id: int | None,
    include_versions: bool = False,
) -> None:
    dest = _export_dir("filter")
    count = await asyncio.to_thread(
        _run_export_filter, dest, source_filter, quality_min, tag_ids, person_id, include_versions
    )
    log.info("Export filter: %d file(s) → %s", count, dest)


# ---------------------------------------------------------------------------
# Job: export all favourites, sorted by person into sub-folders
# ---------------------------------------------------------------------------

def _run_export_by_person(dest: Path) -> int:
    with SessionLocal() as session:
        rows = _base_favourite_query(session)
        count = 0
        for instance, _asset, person in rows:
            src = Path(instance.path)
            if not src.exists():
                continue
            if person is None or person.is_unknown:
                folder = dest / "_unbekannt"
            else:
                folder = dest / _safe_name(person.name or f"person_{person.id}")
            _copy_file(src, folder / src.name)
            count += 1
        return count


async def run_export_by_person_job(status: JobStatus) -> None:
    dest = _export_dir("nach_person")
    count = await asyncio.to_thread(_run_export_by_person, dest)
    log.info("Export by_person: %d file(s) → %s", count, dest)


# ---------------------------------------------------------------------------
# Job: random favourites export — count sets × images each, distinct, no dupes
# ---------------------------------------------------------------------------

def _run_export_random(dest: Path, count: int, images_per_set: int) -> int:
    with SessionLocal() as session:
        rows = _base_favourite_query(session)
        pool: list[tuple[Path, str]] = []
        for instance, _asset, person in rows:
            src = Path(instance.path)
            if not src.exists():
                continue
            person_part = ""
            if person is not None and not person.is_unknown:
                person_part = _safe_name(person.name or f"p{person.id}")
            pool.append((src, person_part))

        total_needed = count * images_per_set
        if total_needed > len(pool):
            # Draw with replacement per set when pool is too small
            sets = [random.sample(pool, min(images_per_set, len(pool))) for _ in range(count)]
        else:
            shuffled = pool[:]
            random.shuffle(shuffled)
            sets = [shuffled[i * images_per_set:(i + 1) * images_per_set] for i in range(count)]

        copied = 0
        for set_index, image_set in enumerate(sets):
            set_dir = dest / f"set_{set_index + 1:02d}"
            for src, person_part in image_set:
                prefix = f"{person_part}_" if person_part else ""
                dest_name = f"{prefix}{src.name}"
                _copy_file(src, set_dir / dest_name)
                copied += 1
        return copied


async def run_export_random_job(status: JobStatus, count: int, images_per_set: int) -> None:
    dest = _export_dir("zufall")
    copied = await asyncio.to_thread(_run_export_random, dest, count, images_per_set)
    log.info("Export random: %d×%d → %d file(s) in %s", count, images_per_set, copied, dest)


# ---------------------------------------------------------------------------
# Job: export collection (album)
# ---------------------------------------------------------------------------

def _run_export_collection(dest: Path, collection_id: int) -> int:
    with SessionLocal() as session:
        rows = (
            session.query(AssetInstance, Asset)
            .join(Asset, Asset.id == AssetInstance.asset_id)
            .join(CollectionItem, CollectionItem.asset_id == Asset.id)
            .filter(CollectionItem.collection_id == collection_id)
            .filter(AssetInstance.deleted_at.is_(None))
            .all()
        )
        count = 0
        for instance, _asset in rows:
            src = Path(instance.path)
            if src.exists():
                _copy_file(src, dest / src.name)
                count += 1
        return count


async def run_export_collection_job(status: JobStatus, collection_id: int, label: str) -> None:
    dest = _export_dir(f"album_{_safe_name(label)}")
    count = await asyncio.to_thread(_run_export_collection, dest, collection_id)
    log.info("Export collection %d (%s): %d file(s) → %s", collection_id, label, count, dest)


# ---------------------------------------------------------------------------
# Enqueue helpers
# ---------------------------------------------------------------------------

async def enqueue_export_filter(
    source_filter: list[str] | None = None,
    quality_min: float | None = None,
    tag_ids: list[int] | None = None,
    person_id: int | None = None,
    include_versions: bool = False,
) -> JobStatus:
    label = "Export Favoriten (Filter + Ableitungen)" if include_versions else "Export Favoriten (Filter)"
    return await job_queue.enqueue(
        kind=JobKind.EXPORT,
        label=label,
        coro_factory=lambda s: run_export_filter_job(
            s, source_filter, quality_min, tag_ids, person_id, include_versions
        ),
    )


async def enqueue_export_by_person() -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.EXPORT,
        label="Export alle Favoriten nach Person",
        coro_factory=lambda s: run_export_by_person_job(s),
    )


async def enqueue_export_random(count: int, images_per_set: int) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.EXPORT,
        label=f"Zufalls-Export {count}×{images_per_set}",
        coro_factory=lambda s: run_export_random_job(s, count, images_per_set),
    )


async def enqueue_export_collection(collection_id: int, label: str) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.EXPORT,
        label=f'Export Album "{label}"',
        coro_factory=lambda s: run_export_collection_job(s, collection_id, label),
    )


def reveal_export_folder() -> None:
    """Open the _export directory in the system file browser."""
    export_root = get_data_root() / _EXPORT_ROOT
    export_root.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(export_root)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(export_root)])
    else:
        subprocess.Popen(["xdg-open", str(export_root)])
