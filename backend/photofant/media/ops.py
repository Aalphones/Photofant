"""Pillow-based image operations for the Editor (P8).

Each op: pydantic schema validates params, then a function transforms the image.
Preview runs on a downscaled working copy; final render (Phase 4) uses original resolution.
Percentages are resolution-independent — rounding happens at the target resolution.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from PIL import Image
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


# ── Param Schemas ────────────────────────────────────────────────────────────

class CropParams(BaseModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    w: float = Field(gt=0, le=100)
    h: float = Field(gt=0, le=100)


class RotateParams(BaseModel):
    dir: Literal["cw", "ccw", "180", "free"] = "cw"
    angle: float = Field(default=0, ge=-360, le=360)


class MirrorParams(BaseModel):
    axis: Literal["h", "v"] = "h"


class PadParams(BaseModel):
    target: str = Field(default="1:1")
    color: str = Field(default="#000000")


class ConvertParams(BaseModel):
    format: Literal["png", "jpeg"] = "png"
    quality: int = Field(default=92, ge=1, le=100)


# ── Implementations ──────────────────────────────────────────────────────────

def _apply_crop(img: Image.Image, params: CropParams) -> Image.Image:
    img_w, img_h = img.size
    left = round(params.x / 100 * img_w)
    top = round(params.y / 100 * img_h)
    right = min(img_w, left + round(params.w / 100 * img_w))
    bottom = min(img_h, top + round(params.h / 100 * img_h))
    if right <= left or bottom <= top:
        return img
    return img.crop((left, top, right, bottom))


_STEP_ANGLES: dict[str, float] = {"cw": -90.0, "ccw": 90.0, "180": 180.0}


def _apply_rotate(img: Image.Image, params: RotateParams) -> Image.Image:
    if params.dir == "free":
        if params.angle == 0:
            return img
        fill = (0, 0, 0) if img.mode == "RGB" else (0, 0, 0, 0)
        return img.rotate(
            -params.angle,
            expand=True,
            resample=Image.Resampling.BICUBIC,
            fillcolor=fill,
        )
    angle = _STEP_ANGLES.get(params.dir, -90.0)
    return img.rotate(angle, expand=True)


def _apply_mirror(img: Image.Image, params: MirrorParams) -> Image.Image:
    transpose = (
        Image.Transpose.FLIP_LEFT_RIGHT
        if params.axis == "h"
        else Image.Transpose.FLIP_TOP_BOTTOM
    )
    return img.transpose(transpose)


def _parse_ratio(ratio_str: str) -> tuple[int, int]:
    parts = ratio_str.split(":")
    if len(parts) == 2:
        try:
            w_val, h_val = int(parts[0]), int(parts[1])
            if w_val > 0 and h_val > 0:
                return (w_val, h_val)
        except ValueError:
            pass
    return (1, 1)


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    if len(hex_str) != 6:
        return (0, 0, 0)
    return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


def _apply_pad(img: Image.Image, params: PadParams) -> Image.Image:
    width, height = img.size
    ratio_w, ratio_h = _parse_ratio(params.target)
    target_aspect = ratio_w / ratio_h
    current_aspect = width / height

    if abs(current_aspect - target_aspect) < 0.001:
        return img

    if current_aspect > target_aspect:
        target_w = width
        target_h = round(width * ratio_h / ratio_w)
    else:
        target_h = height
        target_w = round(height * ratio_w / ratio_h)

    if target_w == width and target_h == height:
        return img

    offset_x = (target_w - width) // 2
    offset_y = (target_h - height) // 2

    if params.color == "transparent":
        padded = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        src = img.convert("RGBA") if img.mode != "RGBA" else img
        padded.paste(src, (offset_x, offset_y))
        return padded

    fill = _hex_to_rgb(params.color)
    padded = Image.new("RGB", (target_w, target_h), fill)
    if img.mode in ("RGBA", "LA", "PA"):
        alpha = img.split()[-1]
        padded.paste(img, (offset_x, offset_y), mask=alpha)
    else:
        if img.mode != "RGB":
            img = img.convert("RGB")
        padded.paste(img, (offset_x, offset_y))
    return padded


def _apply_convert(img: Image.Image, params: ConvertParams) -> Image.Image:
    if params.format == "jpeg":
        if img.mode in ("RGBA", "LA", "PA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.split()[-1]
            background.paste(img, mask=alpha)
            return background
        if img.mode != "RGB":
            return img.convert("RGB")
        return img
    if img.mode not in ("RGB", "RGBA", "L", "LA", "P", "PA"):
        return img.convert("RGBA")
    return img


# ── Dispatcher ───────────────────────────────────────────────────────────────

def apply_op(img: Image.Image, op: str, raw_params: dict[str, Any]) -> Image.Image:
    """Validate params via pydantic, then apply the operation."""
    if op == "crop":
        return _apply_crop(img, CropParams.model_validate(raw_params))
    if op == "rotate":
        return _apply_rotate(img, RotateParams.model_validate(raw_params))
    if op == "mirror":
        return _apply_mirror(img, MirrorParams.model_validate(raw_params))
    if op == "pad":
        return _apply_pad(img, PadParams.model_validate(raw_params))
    if op == "convert":
        return _apply_convert(img, ConvertParams.model_validate(raw_params))
    if op == "smart_crop":
        return img
    log.warning("Unknown op %r — returning image unchanged", op)
    return img
