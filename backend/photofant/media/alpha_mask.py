"""Alpha-mask embedding — combine source image + canvas mask data URL → RGBA PNG.

Convention (Flux-Fill-Standard):
  Painted area in mask (bright / non-zero) → alpha=0 (transparent) in output → will be inpainted.
  Unpainted area (black / zero) → alpha=255 (opaque) in output → will be kept.
"""
from __future__ import annotations

import base64
import io

from PIL import Image, ImageOps


def embed_mask_as_alpha(image_bytes: bytes, mask_data_url: str) -> bytes:
    """Combine source image with a canvas mask data URL into a RGBA PNG.

    Args:
        image_bytes: Source image file bytes (any PIL-readable format).
        mask_data_url: Canvas mask as base64 data URL (e.g. ``data:image/png;base64,...``).
            Painted pixels must be bright (white) or non-transparent;
            unpainted background must be dark (black) or fully transparent.

    Returns:
        RGBA PNG bytes where masked pixels are transparent (alpha=0).
    """
    # Decode mask
    encoded = mask_data_url.split(",", 1)[1] if "," in mask_data_url else mask_data_url
    mask_bytes = base64.b64decode(encoded)

    source = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    mask_img = Image.open(io.BytesIO(mask_bytes))

    # Use luminance so both opaque-white-on-black and RGBA canvas masks work:
    # Transparent pixels → L=0 (black → keeps alpha=255 after invert).
    # Painted bright pixels → L≈255 (white → alpha=0 after invert = transparent).
    mask_gray = mask_img.convert("L")

    if mask_gray.size != source.size:
        mask_gray = mask_gray.resize(source.size, Image.LANCZOS)

    # Invert: painted (255) → 0 (transparent in output), background (0) → 255 (opaque)
    alpha_channel = ImageOps.invert(mask_gray)

    red, green, blue, _ = source.split()
    result = Image.merge("RGBA", (red, green, blue, alpha_channel))

    output = io.BytesIO()
    result.save(output, format="PNG")
    return output.getvalue()
