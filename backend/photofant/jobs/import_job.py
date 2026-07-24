from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from photofant.config import get_data_root
from photofant.db.models import Asset, AssetInstance, Person, ProcessingLedger
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.media.atomic_io import atomic_copy
from photofant.media.meta import SUPPORTED_EXTENSIONS, ImageMeta, read_meta

log = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _dest_path(data_root: Path, meta: ImageMeta, source_path: Path) -> Path:
    extension = source_path.suffix.lower()
    filename = f"{meta.content_hash}{extension}"
    return data_root / "_unknown" / "photos" / filename


def _import_single(source_path: Path) -> int | None:
    """Import one file; return the new asset id, or None if it was a duplicate."""
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
            atomic_copy(source_path, dest)
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

        return asset.id


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
    files = _expand_paths(paths)
    total = len(files)
    imported = 0
    skipped = 0
    imported_asset_ids: list[int] = []

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
            asset_id = await asyncio.to_thread(_import_single, source_path)
            if asset_id is not None:
                imported_asset_ids.append(asset_id)
                imported += 1
            else:
                skipped += 1

        progress = (index + 1) / total
        job_queue.update(status, progress=progress, state=JobState.RUNNING)

    label_parts = [f"{imported} importiert"]
    if skipped:
        label_parts.append(f"{skipped} übersprungen")
    log.info("Import done: %s", ", ".join(label_parts))

    if imported_asset_ids:
        await _enqueue_pipeline(imported_asset_ids)


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
) -> int | None:
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
            return existing_asset.id

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

        log.info("FS-Drop: new asset %d from %s → person %d", asset.id, source_path.name, person_id)
        return asset.id


async def run_scan_job(status: JobStatus, scan_root: Path) -> None:
    """Find image files under scan_root that are not yet in the DB, then import them.

    Person-folder awareness (FS-Drop, §6.1a): files found in a person folder's
    photos/ or favourites/ subdir are imported with fixed_person=True for that person.
    Supports both legacy person_{id}/ folders and current named-person folders.
    """
    from photofant.media.person_folders import is_importable_person_subfolder, person_id_from_path

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

    imported_asset_ids: list[int] = []
    total = len(path_assignments)
    for index, (file_path, pid) in enumerate(path_assignments):
        if pid is not None:
            asset_id = await asyncio.to_thread(_import_to_person, file_path, pid)
        else:
            asset_id = await asyncio.to_thread(_import_single, file_path)
        if asset_id is not None:
            imported_asset_ids.append(asset_id)
        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)

    if imported_asset_ids:
        await _enqueue_pipeline(imported_asset_ids)


async def run_person_import_job(status: JobStatus, person_id: int, paths: list[str]) -> None:
    """Import files that were uploaded directly to a person's folder (fixed_person)."""
    total = len(paths)
    imported_asset_ids: list[int] = []

    for index, path_str in enumerate(paths):
        file_path = Path(path_str)
        asset_id = await asyncio.to_thread(_import_to_person, file_path, person_id)
        if asset_id is not None:
            imported_asset_ids.append(asset_id)
        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)

    if imported_asset_ids:
        await _enqueue_pipeline(imported_asset_ids)


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


@dataclass(frozen=True)
class PipelineSteps:
    """Which processing steps to enqueue for one asset.

    Import turns everything on that the auto_* settings allow. The catch-up run
    (`reprocess_job`) turns on only what the ledger still says is missing, so a
    photo that just lost its face detection isn't captioned all over again.
    """

    heuristics: bool = True
    tags: bool = True
    caption: bool = True
    embedding: bool = True
    faces: bool = True
    classification: bool = True


def steps_from_settings() -> PipelineSteps:
    """The full pipeline, minus whatever the auto_* settings switch off."""
    from photofant.settings import load_settings

    settings = load_settings()
    auto_face: bool = settings.get("auto_face", True)  # type: ignore[assignment]
    return PipelineSteps(
        heuristics=True,
        tags=settings["auto_tag"],
        caption=settings["auto_caption"],
        embedding=settings["auto_embed"],
        faces=auto_face,
        classification=True,
    )


async def enqueue_pipeline_steps(asset_id: int, steps: PipelineSteps) -> None:
    """Enqueue the selected steps for one asset, wiring up the ordering rules.

    This is *the* place the dependency rules live — both the import pipeline and
    the catch-up run go through here, so the two can never drift apart:

    - FACE waits for TAGGING and CAPTIONING (whichever of them actually runs),
      because face matching moves the file into a person folder.
    - CLASSIFICATION waits for TAGGING and EMBEDDING, its two fusion inputs.

    Only steps that really run are counted as prerequisites — waiting for a
    signal nobody will send would strand the asset forever.
    """
    from photofant.jobs.caption_job import enqueue_caption
    from photofant.jobs.classification_job import enqueue_classification
    from photofant.jobs.classification_pipeline import classification_pipeline
    from photofant.jobs.embedding_job import enqueue_embedding
    from photofant.jobs.face_job import enqueue_face
    from photofant.jobs.face_pipeline import face_pipeline
    from photofant.jobs.heuristics_job import enqueue_heuristics
    from photofant.jobs.tagging_job import enqueue_tagging

    if steps.heuristics:
        await enqueue_heuristics(asset_id)
    if steps.tags:
        await enqueue_tagging(asset_id)
    if steps.caption:
        await enqueue_caption(asset_id)
    if steps.embedding:
        await enqueue_embedding(asset_id)

    if steps.faces:
        face_prereq_count = int(steps.tags) + int(steps.caption)
        if face_prereq_count == 0:
            await enqueue_face(asset_id)
        else:
            face_pipeline.register(asset_id, face_prereq_count)

    if steps.classification:
        classification_prereq_count = int(steps.tags) + int(steps.embedding)
        if classification_prereq_count == 0:
            # No TAGGING or EMBEDDING to wait for — the engine still runs, both
            # fusion inputs simply stay absent.
            await enqueue_classification(asset_id)
        else:
            classification_pipeline.register(asset_id, classification_prereq_count)


async def enqueue_post_import_pipeline(asset_ids: list[int]) -> None:
    """Public entrypoint for other import paths (e.g. ComfyUI edit-as-asset, ADR-013)."""
    await _enqueue_pipeline(asset_ids)


async def _enqueue_pipeline(asset_ids: list[int]) -> None:
    """Enqueue the post-import processing pipeline for freshly imported assets.

    Only asset ids travel through the queue — never file paths. Face matching
    moves an asset into its person folder mid-pipeline, so a path captured here
    would be wrong by the time a later job opens it (see media/asset_paths.py).
    """
    from photofant.jobs.thumbnail_job import enqueue_thumbnails

    # One batched thumbnail job for the whole import — not one per photo, or the
    # job dock would drown in entries.
    await enqueue_thumbnails(asset_ids)

    steps = steps_from_settings()
    for asset_id in asset_ids:
        await enqueue_pipeline_steps(asset_id, steps)
