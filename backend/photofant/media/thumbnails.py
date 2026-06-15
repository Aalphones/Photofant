from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

log = logging.getLogger(__name__)

_JPEG_QUALITY = 85


def generate_thumbnail(source_path: Path, size: int) -> bytes:
    """Return JPEG bytes of a max-size×size thumbnail, EXIF-rotation corrected."""
    try:
        with Image.open(source_path) as img_file:
            img: Image.Image = ImageOps.exif_transpose(img_file) or img_file
            if img.mode not in ("RGB", "RGBA", "L"):
                img = img.convert("RGB")
            if img.mode == "RGBA":
                # Flatten transparency onto white background
                background: Image.Image = Image.new("RGB", img.size, (255, 255, 255))
                alpha = img.split()[3]
                background.paste(img, mask=alpha)
                img = background
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
            return buf.getvalue()
    except (UnidentifiedImageError, OSError) as exc:
        log.warning("Cannot generate thumbnail for %s: %s", source_path, exc)
        raise
