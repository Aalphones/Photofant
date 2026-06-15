from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
)

_EXIF_TAG_DATETIME_ORIGINAL = 36867  # 0x9003


class AssetSource(StrEnum):
    ORIGINAL = "original"
    SDXL = "sdxl"
    FLUX = "flux"
    AI_GENERATED = "ai_generated"


@dataclass
class ImageMeta:
    content_hash: str
    width: int
    height: int
    file_size: int
    format: str
    source: str
    created_at: datetime | None
    generation_meta: dict[str, object] | None


def compute_hash(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _exif_datetime(image: Image.Image) -> datetime | None:
    try:
        exif = image.getexif()
        raw_value = exif.get(_EXIF_TAG_DATETIME_ORIGINAL)
        if raw_value:
            return datetime.strptime(str(raw_value), "%Y:%m:%d %H:%M:%S")
    except Exception as exc:
        log.debug("EXIF datetime read failed: %s", exc)
    return None


def _text_chunks(info: dict[Any, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in info.items() if isinstance(key, str) and isinstance(value, str)}


def _detect_source(chunks: dict[str, str]) -> tuple[str, dict[str, object] | None]:
    """Derive source label and generation_meta from PNG text chunks."""
    if "workflow" in chunks:
        gen_meta: dict[str, object] = {"tool": "comfyui"}
        try:
            workflow_data = json.loads(chunks["workflow"])
            gen_meta["workflow"] = workflow_data
            nodes = list(workflow_data.values()) if isinstance(workflow_data, dict) else []
            class_names = " ".join(
                str(node.get("class_type", "")) for node in nodes if isinstance(node, dict)
            ).lower()
            if "flux" in class_names:
                return AssetSource.FLUX, gen_meta
            if "sdxl" in class_names or "sdxl" in class_names:
                return AssetSource.SDXL, gen_meta
        except (json.JSONDecodeError, AttributeError) as exc:
            log.debug("ComfyUI workflow parse failed: %s", exc)
            gen_meta["workflow_raw"] = chunks["workflow"]
        return AssetSource.AI_GENERATED, gen_meta

    if "parameters" in chunks:
        params_text = chunks["parameters"]
        gen_meta = {"tool": "a1111", "parameters": params_text}
        lower = params_text.lower()
        if "flux" in lower:
            return AssetSource.FLUX, gen_meta
        if "sdxl" in lower or " xl" in lower:
            return AssetSource.SDXL, gen_meta
        return AssetSource.AI_GENERATED, gen_meta

    return AssetSource.ORIGINAL, None


def read_meta(path: Path) -> ImageMeta:
    content_hash = compute_hash(path)
    file_size = path.stat().st_size

    try:
        with Image.open(path) as image:
            width, height = image.size
            img_format = (image.format or path.suffix.lstrip(".")).lower()
            created_at = _exif_datetime(image)
            chunks = _text_chunks(dict(image.info))
            source, generation_meta = _detect_source(chunks)
    except (UnidentifiedImageError, OSError) as exc:
        log.warning("Cannot read image %s: %s — using defaults", path, exc)
        width, height = 0, 0
        img_format = path.suffix.lstrip(".")
        created_at = None
        source, generation_meta = AssetSource.ORIGINAL, None

    return ImageMeta(
        content_hash=content_hash,
        width=width,
        height=height,
        file_size=file_size,
        format=img_format,
        source=source,
        created_at=created_at,
        generation_meta=generation_meta,
    )
