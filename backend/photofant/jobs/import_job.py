from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from photofant.config import get_data_root
from photofant.db.models import Asset, AssetInstance, Person, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.media.meta import SUPPORTED_EXTENSIONS, ImageMeta, read_meta

log = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _dest_path(data_root: Path, meta: ImageMeta, source_path: Path) -> Path:
    extension = source_path.suffix.lower()
    filename = f"{meta.content_hash}{extension}"
    return data_root / "_unknown" / "photos" / filename


def _import_single(source_path: Path) -> str | None:
    """Import one file; return content_hash if newly imported, None if duplicate."""
    meta = read_meta(source_path)

    with SessionLocal() as session:
        # Ledger check: already fully processed?
        ledger = session.get(ProcessingLedger, meta.content_hash)
        if ledger is not None:
            log.info("Skipping %s (hash %s already in ledger)", source_path.name, meta.content_hash[:8])
            return None

        # DB dedupe: asset with same hash?
        existing_asset = session.scalar(select(Asset).where(Asset.content_hash == meta.content_hash))
        if existing_asset is not None:
            log.info("Skipping %s (hash %s already in DB)", source_path.name, meta.content_hash[:8])
            return None

        data_root = get_data_root(session)
        dest = _dest_path(data_root, meta, source_path)

        if not dest.exists():
            shutil.copy2(source_path, dest)
            log.info("Copied %s → %s", source_path.name, dest)

        unknown_person = session.scalar(select(Person).where(Person.is_unknown.is_(True)))
        if unknown_person is None:
            raise RuntimeError("_unknown person row missing — run migrations")

        asset = Asset(
            content_hash=meta.content_hash,
            source=meta.source,
            width=meta.width,
            height=meta.height,
            file_size=meta.file_size,
            format=meta.format,
            generation_meta=meta.generation_meta,
            created_at=meta.created_at,
            imported_at=_now_utc(),
        )
        session.add(asset)
        session.flush()  # get asset.id

        instance = AssetInstance(
            asset_id=asset.id,
            person_id=unknown_person.id,
            path=str(dest.resolve()),
        )
        session.add(instance)

        ledger_entry = ProcessingLedger(content_hash=meta.content_hash)
        session.add(ledger_entry)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            # Race condition: another import beat us — clean up copied file if we created it
            if dest.exists():
                with contextlib.suppress(OSError):
                    dest.unlink()
            log.info("Duplicate detected on commit for %s — skipped", source_path.name)
            return None

    return meta.content_hash


async def run_import_job(status: JobStatus, paths: list[str]) -> None:
    total = len(paths)
    imported = 0
    skipped = 0

    for index, raw_path in enumerate(paths):
        source_path = Path(raw_path)
        if not source_path.is_file():
            log.warning("Import path not found: %s", raw_path)
            skipped += 1
        elif source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            log.info("Skipping unsupported format: %s", source_path.suffix)
            skipped += 1
        else:
            result = await asyncio.to_thread(_import_single, source_path)
            if result is not None:
                imported += 1
            else:
                skipped += 1

        progress = (index + 1) / total
        job_queue.update(status, progress=progress, state=JobState.RUNNING)

    label_parts = [f"{imported} importiert"]
    if skipped:
        label_parts.append(f"{skipped} übersprungen")
    log.info("Import done: %s", ", ".join(label_parts))


async def run_scan_job(status: JobStatus, scan_root: Path) -> None:
    """Find image files under scan_root that are not yet in the DB, then import them."""
    with SessionLocal() as session:
        known_paths: set[str] = {
            str(row[0]) for row in session.execute(select(AssetInstance.path)).all()
        }

    candidates: list[Path] = []
    for extension in SUPPORTED_EXTENSIONS:
        candidates.extend(scan_root.rglob(f"*{extension}"))
        candidates.extend(scan_root.rglob(f"*{extension.upper()}"))

    new_paths = [path for path in candidates if str(path.resolve()) not in known_paths]
    log.info("Scan found %d new files under %s", len(new_paths), scan_root)

    if not new_paths:
        return

    # Reuse import logic for each discovered file
    total = len(new_paths)
    for index, file_path in enumerate(new_paths):
        await asyncio.to_thread(_import_single, file_path)
        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)


async def enqueue_import(paths: list[str]) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.IMPORT,
        label=f"Importiere {len(paths)} Datei(en)",
        coro_factory=lambda job_status: run_import_job(job_status, paths),
    )


async def enqueue_scan(scan_root: Path) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.SCAN,
        label=f"Scan: {scan_root}",
        coro_factory=lambda job_status: run_scan_job(job_status, scan_root),
    )
