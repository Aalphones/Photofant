"""Bulk-Edit job — apply one op to a selection of assets, write version per asset.

POST /api/assets/bulk-edit  →  { asset_ids, op, params, save_mode }

Each asset gets a direct new Version (new_copy), no edit-session involved.
Progress is reported per asset; per-asset errors are collected and logged but
do not abort the remaining batch.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from photofant.db.models import AssetInstance, Person, Version
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.media.ops import ModelNotAvailableError, apply_op, is_orientation_only
from photofant.media.orientation_overwrite import overwrite_instance
from photofant.media.person_folders import ensure_person_folder

log = logging.getLogger(__name__)

_JPEG_QUALITY_DEFAULT = 92


# ── Asset resolution ──────────────────────────────────────────────────────────

def _resolve_bulk_assets(
    asset_ids: list[int],
) -> list[tuple[int, int, int, str]]:
    """Return (asset_id, instance_id, person_id, source_path) for active assets."""
    with SessionLocal() as session:
        from photofant.db.models import Asset
        rows = (
            session.query(Asset.id, AssetInstance.id, AssetInstance.person_id, AssetInstance.path)
            .join(AssetInstance, AssetInstance.asset_id == Asset.id)
            .filter(Asset.id.in_(asset_ids))
            .filter(AssetInstance.deleted_at.is_(None))
            .all()
        )
    return [(int(row[0]), int(row[1]), int(row[2]), str(row[3])) for row in rows]


# ── Image helpers ─────────────────────────────────────────────────────────────

def _determine_format(
    op: str,
    params: dict[str, Any],
    img: Image.Image,
) -> tuple[str, str, int]:
    """Returns (pil_format, extension, quality)."""
    if op == "convert":
        fmt = params.get("format", "png")
        quality = int(params.get("quality", _JPEG_QUALITY_DEFAULT))
        if fmt == "jpeg":
            return ("JPEG", "jpg", quality)
        return ("PNG", "png", 0)
    if img.mode in ("RGBA", "LA", "PA"):
        return ("PNG", "png", 0)
    return ("JPEG", "jpg", _JPEG_QUALITY_DEFAULT)


def _write_image(img: Image.Image, path: Path, pil_format: str, quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pil_format == "JPEG":
        if img.mode in ("RGBA", "LA", "PA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(path, format="JPEG", quality=quality)
    else:
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        img.save(path, format="PNG")


# ── Per-asset processing ──────────────────────────────────────────────────────

def _process_one_asset(
    asset_id: int,
    instance_id: int,
    person_id: int,
    source_path: str,
    op: str,
    params: dict[str, Any],
) -> None:
    from photofant.config import get_data_root

    src = Path(source_path)
    with Image.open(src) as raw:
        img: Image.Image = ImageOps.exif_transpose(raw) or raw
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGB")
        if img.mode == "L":
            img = img.convert("RGB")
        img.load()

    img = apply_op(img, op, params)
    img.load()

    pil_format, ext, quality = _determine_format(op, params, img)
    width, height = img.size

    data_root = Path(get_data_root())
    with SessionLocal() as session:
        person = session.get(Person, person_id)
        if person is None:
            raise ValueError(f"Person {person_id} not found for asset {asset_id}")
        person_dir = ensure_person_folder(data_root, person)

    edits_dir = person_dir / "edits"
    edits_dir.mkdir(parents=True, exist_ok=True)
    filename = f"edit_{uuid.uuid4().hex[:12]}.{ext}"
    edit_path = edits_dir / filename

    _write_image(img, edit_path, pil_format, quality)

    with SessionLocal() as session:
        for ver in (
            session.query(Version)
            .filter(Version.instance_id == instance_id, Version.is_current.is_(True))
            .all()
        ):
            ver.is_current = False

        version = Version(
            instance_id=instance_id,
            face_id=None,
            type=op,
            parent_id=None,
            path=str(edit_path.resolve()),
            is_current=True,
            params={"steps": [{"op": op, "params": params}], "width": width, "height": height},
            created_at=datetime.now(UTC),
        )
        session.add(version)
        session.commit()
        version_id = version.id

    _generate_version_thumbnail(version_id, edit_path)
    log.info("Bulk-edit version %d created for asset %d (op=%s)", version_id, asset_id, op)


# ── Orientation-only overwrite (rotate/mirror skip the version pipeline) ──────

def _process_one_asset_orientation(
    asset_id: int,
    instance_id: int,
    op: str,
    params: dict[str, Any],
) -> None:
    """Overwrite every instance of `asset_id` in place instead of creating a version.

    Mirrors the editor's Phase-3 overwrite (see media.orientation_overwrite) —
    `overwrite_instance` already fans out to every sibling instance of the
    asset itself, so this only needs to resolve the one instance row that
    triggered this asset into the batch.
    """
    steps = [{"op": op, "params_dict": params}]
    with SessionLocal() as session:
        instance = session.get(AssetInstance, instance_id)
        if instance is None:
            raise ValueError(f"AssetInstance {instance_id} not found for asset {asset_id}")
        overwrite_instance(session, instance, steps)
    log.info("Bulk-edit orientation overwrite done for asset %d (op=%s)", asset_id, op)


def _generate_version_thumbnail(version_id: int, file_path: Path) -> None:
    from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
    from photofant.media.thumbnails import generate_thumbnail

    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    for size in (256, 512):
        try:
            thumb = generate_thumbnail(file_path, size)
            store_thumbnail(cache_path, version_id, size, thumb, "edit")
        except Exception:
            log.exception("Thumbnail failed for bulk-edit version %d (size=%d)", version_id, size)


# ── Job coroutine ─────────────────────────────────────────────────────────────

async def run_bulk_edit_job(
    status: JobStatus,
    asset_ids: list[int],
    op: str,
    params: dict[str, Any],
) -> None:
    import asyncio

    assets = await asyncio.to_thread(_resolve_bulk_assets, asset_ids)
    total = max(len(assets), 1)
    errors: list[str] = []

    job_queue.update(status, progress=0.0, state=JobState.RUNNING)

    orientation_only = is_orientation_only([{"op": op, "params_dict": params}])
    processed_assets: set[int] = set()

    for index, (asset_id, instance_id, person_id, source_path) in enumerate(assets):
        try:
            if orientation_only:
                # Every AssetInstance row of a multi-person photo resolves to the
                # same asset_id here — overwrite_instance already transforms all
                # of them in one go, so later rows for an already-done asset skip.
                if asset_id not in processed_assets:
                    await asyncio.to_thread(
                        _process_one_asset_orientation,
                        asset_id, instance_id, op, params,
                    )
                    processed_assets.add(asset_id)
            else:
                await asyncio.to_thread(
                    _process_one_asset,
                    asset_id, instance_id, person_id, source_path, op, params,
                )
        except ModelNotAvailableError as exc:
            error_msg = f"Asset {asset_id}: model unavailable for op '{exc.op}' (role '{exc.role}')"
            errors.append(error_msg)
            log.warning("Bulk-edit skipped %d: %s", asset_id, error_msg)
        except Exception as exc:
            error_msg = f"Asset {asset_id}: {exc}"
            errors.append(error_msg)
            log.exception("Bulk-edit failed for asset %d", asset_id)

        job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)

    if errors:
        log.warning("Bulk-edit finished with %d error(s):\n%s", len(errors), "\n".join(errors))
    log.info("Bulk-edit done: %d asset(s), %d error(s)", len(assets), len(errors))


async def enqueue_bulk_edit(
    asset_ids: list[int],
    op: str,
    params: dict[str, Any],
) -> JobStatus:
    count = len(asset_ids)
    return await job_queue.enqueue(
        kind=JobKind.BULK_EDIT,
        label=f"Bulk-Edit {count} Bild(er): {op}",
        coro_factory=lambda job_status: run_bulk_edit_job(job_status, asset_ids, op, params),
    )
