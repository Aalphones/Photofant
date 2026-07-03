"""Orientation-only overwrite — rotate/mirror mutate the source in place (Editor Phase 3).

An edit session containing only rotate/mirror steps (see media.ops.is_orientation_only)
skips the normal Versions pipeline entirely: no new Version row, no `edits/` copy.
The source file (instance/face/version target) is transformed in place at full
resolution and dependent data is refreshed to match.

Multi-instance rationale (kind="instance" only): AssetInstance.path is a
per-person physical copy, but Asset.{content_hash,width,height,phash,file_size,
format} and the gallery thumbnail cache (db.cache, target_kind="asset") are
keyed by asset_id and shared across every instance of a multi-person photo
(see api/assets.py:_active_row, which arbitrarily picks one instance to
represent the asset). Rotating only the edited instance would silently desync
that shared record from the untouched sibling copies, so every active sibling
instance is transformed too, before the Asset row is refreshed once from the
edited (target) instance. (User decision 2026-07-03, editor-basis-fixes Phase 3.)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.cache import delete_thumbnails, get_cache_db_path, init_cache_db, store_thumbnail
from photofant.db.models import Asset, AssetInstance, Face, ProcessingLedger, Version
from photofant.media.meta import compute_hash
from photofant.media.ops import apply_op, transform_bbox
from photofant.media.phash import compute_phash, compute_phash_hex
from photofant.media.thumbnails import generate_thumbnail

log = logging.getLogger(__name__)

_JPEG_QUALITY = 92


def _render_in_place(source_path: Path, steps: list[dict[str, Any]]) -> tuple[Image.Image, tuple[int, int], str]:
    """Apply orientation steps at full resolution.

    Returns (final image, pre-transform size, PIL format). The pre-transform
    size is post-exif_transpose — the same space the editor previewed and the
    space Face.bbox coordinates must be re-mapped from.
    """
    with Image.open(source_path) as raw:
        pil_format = raw.format or "JPEG"
        img: Image.Image = ImageOps.exif_transpose(raw) or raw
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGB")
        if img.mode == "L":
            img = img.convert("RGB")
        pre_size = img.size
        for step in steps:
            img = apply_op(img, step["op"], step["params_dict"])
        img.load()
    return img, pre_size, pil_format


def _save_in_place(img: Image.Image, path: Path, pil_format: str) -> None:
    if pil_format == "JPEG":
        if img.mode in ("RGBA", "LA", "PA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(path, format="JPEG", quality=_JPEG_QUALITY)
    else:
        img.save(path, format=pil_format)


# ── kind="version" ────────────────────────────────────────────────────────────

def overwrite_version(db: Session, version: Version, steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Overwrite a specific Version's file in place; update its own params/thumbnail."""
    path = Path(version.path)
    img, _pre_size, pil_format = _render_in_place(path, steps)
    _save_in_place(img, path, pil_format)
    width, height = img.size

    params = dict(version.params or {})
    params["width"] = width
    params["height"] = height
    version.params = params
    db.commit()

    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    for size in (256, 512):
        thumb = generate_thumbnail(path, size)
        store_thumbnail(cache_path, version.id, size, thumb, "edit")

    return {"width": width, "height": height}


# ── kind="face" ───────────────────────────────────────────────────────────────

def overwrite_face(db: Session, face: Face, steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Overwrite a Face crop file in place; refresh resolution/phash + thumbnail."""
    path = Path(face.crop_path)
    img, _pre_size, pil_format = _render_in_place(path, steps)
    _save_in_place(img, path, pil_format)
    width, height = img.size

    face.resolution = width * height
    try:
        face.phash = compute_phash_hex(path)
    except Exception:
        log.exception("overwrite_face: phash computation failed for face %d", face.id)
    db.commit()

    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    thumb = generate_thumbnail(path, 256)
    store_thumbnail(cache_path, face.id, 256, thumb, "face")

    return {"width": width, "height": height}


# ── kind="instance" (multi-instance aware) ────────────────────────────────────

def overwrite_instance(db: Session, instance: AssetInstance, steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Overwrite every active AssetInstance of the same asset, then refresh the
    shared Asset row and every Face.bbox on that asset once from the edited
    (target) instance. See module docstring for the multi-instance rationale.
    """
    asset = db.get(Asset, instance.asset_id)
    if asset is None:
        raise ValueError(f"Asset {instance.asset_id} not found for instance {instance.id}")

    siblings = db.scalars(
        select(AssetInstance).where(
            AssetInstance.asset_id == asset.id,
            AssetInstance.deleted_at.is_(None),
            AssetInstance.id != instance.id,
        )
    ).all()

    target_path = Path(instance.path)
    target_img, target_pre_size, target_pil_format = _render_in_place(target_path, steps)
    _save_in_place(target_img, target_path, target_pil_format)
    target_final_size = target_img.size

    for sibling in siblings:
        sibling_path = Path(sibling.path)
        sib_img, sib_pre_size, sib_pil_format = _render_in_place(sibling_path, steps)
        if sib_pre_size != target_pre_size:
            log.warning(
                "overwrite_instance: sibling instance %d pre-transform size %s differs "
                "from target instance %d size %s (asset %d) — sibling had already "
                "diverged; transforming anyway, bbox space follows the target instance",
                sibling.id, sib_pre_size, instance.id, target_pre_size, asset.id,
            )
        _save_in_place(sib_img, sibling_path, sib_pil_format)

    old_content_hash = asset.content_hash
    new_content_hash = compute_hash(target_path)
    width, height = target_final_size

    asset.content_hash = new_content_hash
    asset.width = width
    asset.height = height
    asset.file_size = target_path.stat().st_size
    asset.format = target_pil_format.lower()
    try:
        asset.phash = compute_phash(target_path)
    except Exception:
        log.exception("overwrite_instance: asset phash computation failed for asset %d", asset.id)

    _rekey_processing_ledger(db, old_content_hash, new_content_hash)

    faces = db.scalars(select(Face).where(Face.asset_id == asset.id)).all()
    for face in faces:
        if face.bbox is None:
            continue
        face.bbox = transform_bbox(face.bbox, steps, target_pre_size)

    db.commit()

    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    delete_thumbnails(cache_path, asset.id, target_kind="asset")

    return {"width": width, "height": height, "asset_id": asset.id}


def _rekey_processing_ledger(db: Session, old_hash: str, new_hash: str) -> None:
    """Move the ledger row from the pre-edit content_hash to the post-edit one."""
    if old_hash == new_hash:
        return
    old_ledger = db.get(ProcessingLedger, old_hash)
    if old_ledger is None:
        return
    if db.get(ProcessingLedger, new_hash) is not None:
        log.warning(
            "overwrite_instance: ledger row for %s already exists — dropping stale %s",
            new_hash, old_hash,
        )
        db.delete(old_ledger)
        return

    flags = {
        "faces_done": old_ledger.faces_done,
        "tags_done": old_ledger.tags_done,
        "caption_done": old_ledger.caption_done,
        "embedding_done": old_ledger.embedding_done,
        "heuristics_done": old_ledger.heuristics_done,
        "classified": old_ledger.classified,
    }
    db.delete(old_ledger)
    db.flush()
    db.add(ProcessingLedger(content_hash=new_hash, **flags))
