from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError

from photofant.config import get_data_root
from photofant.db.models import Asset, AssetInstance, Person, ProcessingLedger, ReviewItem
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.media.meta import SUPPORTED_EXTENSIONS, ImageMeta, read_meta
from photofant.media.phash import compute_phash, find_similar

log = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _dest_path(data_root: Path, meta: ImageMeta, source_path: Path) -> Path:
    extension = source_path.suffix.lower()
    filename = f"{meta.content_hash}{extension}"
    return data_root / "_unknown" / "photos" / filename


def _import_single(source_path: Path, dupe_threshold: int) -> tuple[int, str] | None:
    """Import one file; return (asset_id, dest_path) if newly imported, None if duplicate."""
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

        data_root = get_data_root()
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

        # --- pHash + dupe detection (separate commit so import stays intact on failure) ---
        try:
            phash_val = compute_phash(dest)
            asset.phash = phash_val
            session.commit()

            similar = find_similar(session, phash_val, asset.id, dupe_threshold)
            for other_id, distance in similar:
                asset_a_id = min(asset.id, other_id)
                asset_b_id = max(asset.id, other_id)
                stmt = sqlite_insert(ReviewItem).values(
                    type="dupe_candidate",
                    asset_a_id=asset_a_id,
                    asset_b_id=asset_b_id,
                    phash_distance=distance,
                    created_at=_now_utc(),
                ).on_conflict_do_nothing()
                session.execute(stmt)
            if similar:
                session.commit()
                log.info(
                    "pHash: %d similar asset(s) found for %s (threshold=%d)",
                    len(similar),
                    source_path.name,
                    dupe_threshold,
                )
        except Exception:
            log.exception("pHash/dupe-detection failed for %s — continuing", source_path.name)
            session.rollback()

        return asset.id, str(dest.resolve())


def _expand_paths(raw_paths: list[str]) -> list[Path]:
    """Flatten input paths: directories are walked recursively for supported images.

    Files are kept as-is (extension is validated later). Duplicate paths
    (e.g. case-insensitive filesystems matching both globs) are removed,
    preserving first-seen order.
    """
    collected: list[Path] = []
    for raw_path in raw_paths:
        path = Path(raw_path)
        if path.is_dir():
            for extension in SUPPORTED_EXTENSIONS:
                collected.extend(path.rglob(f"*{extension}"))
                collected.extend(path.rglob(f"*{extension.upper()}"))
        else:
            collected.append(path)

    seen: set[str] = set()
    unique: list[Path] = []
    for file_path in collected:
        key = str(file_path.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(file_path)
    return unique


async def run_import_job(status: JobStatus, paths: list[str]) -> None:
    from photofant.settings import load_settings

    settings = load_settings()
    dupe_threshold = settings["dupe_threshold"]

    files = _expand_paths(paths)
    total = len(files)
    imported = 0
    skipped = 0
    imported_items: list[tuple[int, str]] = []

    if total == 0:
        log.warning("Import: no importable files found in %d input path(s)", len(paths))
        return

    for index, source_path in enumerate(files):
        if not source_path.is_file():
            log.warning("Import path not found: %s", source_path)
            skipped += 1
        elif source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            log.info("Skipping unsupported format: %s", source_path.suffix)
            skipped += 1
        else:
            result = await asyncio.to_thread(_import_single, source_path, dupe_threshold)
            if result is not None:
                imported_items.append(result)
                imported += 1
            else:
                skipped += 1

        progress = (index + 1) / total
        job_queue.update(status, progress=progress, state=JobState.RUNNING)

    label_parts = [f"{imported} importiert"]
    if skipped:
        label_parts.append(f"{skipped} übersprungen")
    log.info("Import done: %s", ", ".join(label_parts))

    if imported_items:
        await _enqueue_pipeline(imported_items)


async def run_scan_job(status: JobStatus, scan_root: Path) -> None:
    """Find image files under scan_root that are not yet in the DB, then import them."""
    from photofant.settings import load_settings

    settings = load_settings()
    dupe_threshold = settings["dupe_threshold"]

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

    imported_items: list[tuple[int, str]] = []
    total = len(new_paths)
    for index, file_path in enumerate(new_paths):
        result = await asyncio.to_thread(_import_single, file_path, dupe_threshold)
        if result is not None:
            imported_items.append(result)
        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)

    if imported_items:
        await _enqueue_pipeline(imported_items)


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


async def _enqueue_pipeline(items: list[tuple[int, str]]) -> None:
    """Enqueue the post-import processing pipeline for freshly imported assets.

    Thumbnails and heuristics always run; tagging, captioning and embedding are
    gated on the auto_* settings flags so a user can disable expensive ML steps.
    """
    from photofant.jobs.thumbnail_job import enqueue_thumbnails
    from photofant.settings import load_settings

    settings = load_settings()

    await enqueue_thumbnails(items)
    await _enqueue_heuristics_batch(items)
    if settings["auto_tag"]:
        await _enqueue_tagging_batch(items)
    if settings["auto_caption"]:
        await _enqueue_caption_batch(items)
    if settings["auto_embed"]:
        await _enqueue_embedding_batch(items)


async def _enqueue_heuristics_batch(items: list[tuple[int, str]]) -> None:
    from photofant.jobs.heuristics_job import enqueue_heuristics

    for asset_id, asset_path in items:
        await enqueue_heuristics(asset_id, asset_path)


async def _enqueue_tagging_batch(items: list[tuple[int, str]]) -> None:
    from photofant.jobs.tagging_job import enqueue_tagging

    for asset_id, asset_path in items:
        await enqueue_tagging(asset_id, asset_path)


async def _enqueue_caption_batch(items: list[tuple[int, str]]) -> None:
    from photofant.jobs.caption_job import enqueue_caption

    for asset_id, asset_path in items:
        await enqueue_caption(asset_id, asset_path)


async def _enqueue_embedding_batch(items: list[tuple[int, str]]) -> None:
    from photofant.jobs.embedding_job import enqueue_embedding

    for asset_id, asset_path in items:
        await enqueue_embedding(asset_id, asset_path)
