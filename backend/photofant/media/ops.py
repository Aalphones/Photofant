"""Pillow-based image operations for the Editor (P8).

Each op: pydantic schema validates params, then a function transforms the image.
Preview runs on a downscaled working copy; final render (Phase 4) uses original resolution.
Percentages are resolution-independent — rounding happens at the target resolution.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from PIL import Image
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class ModelNotAvailableError(Exception):
    """Raised when an inference op requires a model role that is not enabled."""

    def __init__(self, op: str, role: str) -> None:
        super().__init__(f"Op '{op}' requires role '{role}' but no model is enabled")
        self.op = op
        self.role = role


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


class RembgParams(BaseModel):
    pass


class SmartCropParams(BaseModel):
    pass


# ── Model path resolution ─────────────────────────────────────────────────────

def _resolve_rembg_model_path() -> str | None:
    """Return filesystem path of the enabled rembg-u2net model, or None."""
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as db:
        entry = db.query(ModelRegistry).filter_by(manifest_id="rembg-u2net", enabled=True).first()
        if entry is None or not entry.path:
            return None
        path = Path(entry.path)
        return str(path) if path.exists() else None


def _resolve_buffalo_l_dir() -> str | None:
    """Return model directory for buffalo_l if enabled, or None."""
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as db:
        entry = db.query(ModelRegistry).filter_by(manifest_id="buffalo_l", enabled=True).first()
        if entry is None or not entry.path:
            return None
        path = Path(entry.path)
        return str(path) if path.exists() else None


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


def _apply_rembg(img: Image.Image, _params: RembgParams) -> Image.Image:
    """Remove background via u2net ONNX. Returns RGBA image with alpha mask."""
    import numpy as np

    from photofant.inference.session_manager import session_manager

    model_path = _resolve_rembg_model_path()
    if model_path is None:
        raise ModelNotAvailableError("rembg", "rembg")

    orig_size = img.size  # (W, H)
    img_rgb = img.convert("RGB")

    # Preprocess: resize to 320×320 and normalize with ImageNet stats
    resized = img_rgb.resize((320, 320), Image.Resampling.BILINEAR)
    np_resized = np.array(resized, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    blob = ((np_resized - mean) / std).transpose(2, 0, 1)[np.newaxis, :].astype(np.float32)

    try:
        session = session_manager.acquire_session(model_path)
        try:
            input_name = session.get_inputs()[0].name
            output_name = session.get_outputs()[0].name
            raw_output = session.run([output_name], {input_name: blob})[0]
        finally:
            session_manager.release_session(model_path)
    except RuntimeError as exc:
        raise ModelNotAvailableError("rembg", "rembg") from exc

    # Squeeze mask, clip to [0, 1], resize back to original dimensions
    mask_320 = np.clip(raw_output.squeeze(), 0.0, 1.0)
    mask_pil = Image.fromarray((mask_320 * 255).astype(np.uint8), mode="L")
    mask_orig = mask_pil.resize(orig_size, Image.Resampling.BILINEAR)

    result = img_rgb.convert("RGBA")
    result.putalpha(mask_orig)
    return result


def _apply_smart_crop(img: Image.Image, _params: SmartCropParams) -> Image.Image:
    """Detect best face via SCRFD and return a 3× face-size centered crop."""
    import numpy as np

    from photofant.inference.adapters.buffalo_l import (
        _DET_INPUT_SIZE,
        _decode_scrfd_outputs,
        _make_scrfd_blob,
    )
    from photofant.inference.session_manager import session_manager

    buffalo_dir = _resolve_buffalo_l_dir()
    if buffalo_dir is None:
        raise ModelNotAvailableError("smart_crop", "face")

    det_path = str(Path(buffalo_dir) / "det_10g.onnx")
    np_img = np.array(img.convert("RGB"), dtype=np.uint8)

    try:
        blob, scale = _make_scrfd_blob(np_img)
        sess = session_manager.acquire_session(det_path)
        try:
            input_name = sess.get_inputs()[0].name
            out_names = [output.name for output in sess.get_outputs()]
            raw = sess.run(out_names, {input_name: blob})
            det_outputs = dict(zip(out_names, raw, strict=True))
        finally:
            session_manager.release_session(det_path)
    except RuntimeError as exc:
        raise ModelNotAvailableError("smart_crop", "face") from exc

    faces = _decode_scrfd_outputs(det_outputs, _DET_INPUT_SIZE, _DET_INPUT_SIZE, scale)
    if not faces:
        log.info("smart_crop: no faces detected, returning image unchanged")
        return img

    best = max(faces, key=lambda face: face["score"])
    x1, y1, x2, y2 = best["bbox"]

    # Center on face, pad to 3× the face dimension on each axis
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    half = max(x2 - x1, y2 - y1) * 1.5

    img_w, img_h = img.size
    crop_x1 = max(0.0, cx - half)
    crop_y1 = max(0.0, cy - half)
    crop_x2 = min(float(img_w), cx + half)
    crop_y2 = min(float(img_h), cy + half)

    return img.crop((int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)))


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
    if op == "rembg":
        return _apply_rembg(img, RembgParams.model_validate(raw_params))
    if op == "smart_crop":
        return _apply_smart_crop(img, SmartCropParams.model_validate(raw_params))
    log.warning("Unknown op %r — returning image unchanged", op)
    return img


