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


def _is_scannable(file_path: Path, data_root: Path) -> bool:
    """Filter out paths inside .photofant/, faces/, and edits/ directories."""
    try:
        relative = file_path.resolve().relative_to(data_root.resolve())
    except ValueError:
        return True
    parts = relative.parts
    if not parts:
        return False
    if parts[0] == ".photofant":
        return False
    return not (len(parts) >= 2 and parts[1] in ("faces", "edits"))


def _import_to_person(
    source_path: Path,
    person_id: int,
    dupe_threshold: int,
) -> tuple[int, str] | None:
    """Import a file dropped into a person folder (FS-Drop, §6.1a).

    If the asset already exists (same hash), creates a new instance for the
    person. Otherwise creates a full new asset. In both cases the file stays
    in place and fixed_person is set.
    """
    meta = read_meta(source_path)

    with SessionLocal() as session:
        person = session.get(Person, person_id)
        if person is None:
            log.warning("FS-Drop: person %d not found — skipping %s", person_id, source_path.name)
            return None

        existing_asset = session.scalar(select(Asset).where(Asset.content_hash == meta.content_hash))

        if existing_asset is not None:
            existing_instance = session.scalar(
                select(AssetInstance).where(
                    AssetInstance.asset_id == existing_asset.id,
                    AssetInstance.person_id == person_id,
                    AssetInstance.deleted_at.is_(None),
                )
            )
            if existing_instance is not None:
                log.info(
                    "FS-Drop: instance exists for asset %d + person %d — skipping",
                    existing_asset.id, person_id,
                )
                return None

            instance = AssetInstance(
                asset_id=existing_asset.id,
                person_id=person_id,
                path=str(source_path.resolve()),
                fixed_person=True,
            )
            session.add(instance)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return None

            log.info(
                "FS-Drop: new instance for existing asset %d → person %d",
                existing_asset.id, person_id,
            )
            return existing_asset.id, str(source_path.resolve())

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
        session.flush()

        instance = AssetInstance(
            asset_id=asset.id,
            person_id=person_id,
            path=str(source_path.resolve()),
            fixed_person=True,
        )
        session.add(instance)

        ledger_entry = ProcessingLedger(content_hash=meta.content_hash)
        session.add(ledger_entry)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            log.info("FS-Drop: duplicate on commit for %s — skipped", source_path.name)
            return None

        try:
            phash_val = compute_phash(source_path)
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
        except Exception:
            log.exception("pHash/dupe-detection failed for FS-Drop %s", source_path.name)
            session.rollback()

        log.info("FS-Drop: new asset %d from %s → person %d", asset.id, source_path.name, person_id)
        return asset.id, str(source_path.resolve())


async def run_scan_job(status: JobStatus, scan_root: Path) -> None:
    """Find image files under scan_root that are not yet in the DB, then import them.

    Person-folder awareness (FS-Drop, §6.1a): files found in a person folder's
    photos/ or favourites/ subdir are imported with fixed_person=True for that person.
    Supports both legacy person_{id}/ folders and current named-person folders.
    """
    from photofant.media.person_folders import is_importable_person_subfolder, person_id_from_path
    from photofant.settings import load_settings

    settings = load_settings()
    dupe_threshold = settings["dupe_threshold"]

    candidates: list[Path] = []
    for extension in SUPPORTED_EXTENSIONS:
        candidates.extend(scan_root.rglob(f"*{extension}"))
        candidates.extend(scan_root.rglob(f"*{extension.upper()}"))

    # Resolve person assignments and filter new paths while the session is open,
    # so named-folder lookups can use the DB.
    path_assignments: list[tuple[Path, int | None]] = []
    with SessionLocal() as session:
        known_paths: set[str] = {
            str(row[0]) for row in session.execute(select(AssetInstance.path)).all()
        }
        new_paths = [
            path for path in candidates
            if str(path.resolve()) not in known_paths and _is_scannable(path, scan_root)
        ]
        log.info("Scan found %d new files under %s", len(new_paths), scan_root)

        for file_path in new_paths:
            pid = person_id_from_path(file_path, scan_root, session)
            importable = pid is not None and is_importable_person_subfolder(file_path, scan_root, session)
            path_assignments.append((file_path, pid if importable else None))

    if not path_assignments:
        return

    imported_items: list[tuple[int, str]] = []
    total = len(path_assignments)
    for index, (file_path, pid) in enumerate(path_assignments):
        if pid is not None:
            result = await asyncio.to_thread(_import_to_person, file_path, pid, dupe_threshold)
        else:
            result = await asyncio.to_thread(_import_single, file_path, dupe_threshold)
        if result is not None:
            imported_items.append(result)
        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)

    if imported_items:
        await _enqueue_pipeline(imported_items)


async def run_person_import_job(status: JobStatus, person_id: int, paths: list[str]) -> None:
    """Import files that were uploaded directly to a person's folder (fixed_person)."""
    from photofant.settings import load_settings

    settings = load_settings()
    dupe_threshold = settings["dupe_threshold"]

    total = len(paths)
    imported_items: list[tuple[int, str]] = []

    for index, path_str in enumerate(paths):
        file_path = Path(path_str)
        result = await asyncio.to_thread(_import_to_person, file_path, person_id, dupe_threshold)
        if result is not None:
            imported_items.append(result)
        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)

    if imported_items:
        await _enqueue_pipeline(imported_items)


async def enqueue_person_import(person_id: int, paths: list[str]) -> JobStatus:
    return await job_queue.enqueue(
        kind=JobKind.IMPORT,
        label=f"Importiere {len(paths)} Datei(en) für Person {person_id}",
        coro_factory=lambda job_status: run_person_import_job(job_status, person_id, paths),
    )


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

    Thumbnails and heuristics always run; tagging, captioning, embedding and
    face detection are gated on auto_* settings flags.
    """
    from photofant.jobs.thumbnail_job import enqueue_thumbnails
    from photofant.settings import load_settings

    settings = load_settings()

    await enqueue_thumbnails(items)
    await _enqueue_heuristics_batch(items)
    auto_tag: bool = settings["auto_tag"]
    auto_caption: bool = settings["auto_caption"]
    auto_face: bool = settings.get("auto_face", True)  # type: ignore[assignment]

    if auto_tag:
        await _enqueue_tagging_batch(items)
    if auto_caption:
        await _enqueue_caption_batch(items)
    if settings["auto_embed"]:
        await _enqueue_embedding_batch(items)

    if auto_face:
        prereq_count = int(auto_tag) + int(auto_caption)
        if prereq_count == 0:
            # No TAGGING or CAPTIONING configured — FACE has no prerequisites.
            await _enqueue_face_batch(items)
        else:
            from photofant.jobs.face_pipeline import face_pipeline

            for asset_id, asset_path in items:
                face_pipeline.register(asset_id, asset_path, prereq_count)


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


async def _enqueue_face_batch(items: list[tuple[int, str]]) -> None:
    from photofant.jobs.face_job import enqueue_face

    for asset_id, asset_path in items:
        await enqueue_face(asset_id, asset_path)
