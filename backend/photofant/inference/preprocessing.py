"""Preprocessing utilities — one place for all resize/normalize logic.

Each model family has a canonical preprocessing contract; this module owns it.
Call the right function before passing an image to a model adapter.
"""
from __future__ import annotations

import numpy as np


def resize_pad_square(image: np.ndarray, size: int) -> np.ndarray:
    """Resize image to (size, size) with letter-/pillar-boxing (white background).

    image: uint8 RGB (H, W, 3).
    Returns uint8 RGB (size, size, 3).
    """
    from PIL import Image as PILImage

    pil = PILImage.fromarray(image).convert("RGB")
    original_width, original_height = pil.size
    scale = size / max(original_width, original_height)
    new_width = round(original_width * scale)
    new_height = round(original_height * scale)
    pil = pil.resize((new_width, new_height), PILImage.LANCZOS)
    canvas = PILImage.new("RGB", (size, size), (255, 255, 255))
    offset_x = (size - new_width) // 2
    offset_y = (size - new_height) // 2
    canvas.paste(pil, (offset_x, offset_y))
    return np.asarray(canvas, dtype=np.uint8)


def resize_center_crop(image: np.ndarray, size: int) -> np.ndarray:
    """Resize shortest side to `size` then center-crop to (size, size).

    image: uint8 RGB (H, W, 3).
    Returns uint8 RGB (size, size, 3).
    """
    from PIL import Image as PILImage

    pil = PILImage.fromarray(image).convert("RGB")
    original_width, original_height = pil.size
    scale = size / min(original_width, original_height)
    new_width = round(original_width * scale)
    new_height = round(original_height * scale)
    pil = pil.resize((new_width, new_height), PILImage.LANCZOS)
    left = (new_width - size) // 2
    top = (new_height - size) // 2
    pil = pil.crop((left, top, left + size, top + size))
    return np.asarray(pil, dtype=np.uint8)


def resize_squash(image: np.ndarray, size: int) -> np.ndarray:
    """Resize image to (size, size), ignoring aspect ratio (no crop, no pad).

    image: uint8 RGB (H, W, 3).
    Returns uint8 RGB (size, size, 3).

    Florence-2's reference image processor resizes directly to a square
    (do_center_crop = false) rather than crop — keeping the whole frame visible.
    """
    from PIL import Image as PILImage

    pil = PILImage.fromarray(image).convert("RGB")
    pil = pil.resize((size, size), PILImage.LANCZOS)
    return np.asarray(pil, dtype=np.uint8)


def normalize_imagenet(image: np.ndarray) -> np.ndarray:
    """Normalize uint8 RGB (H, W, 3) to float32 (3, H, W) with ImageNet stats.

    Converts HWC → CHW, scales to [0, 1], applies mean/std.
    Used by CLIP, SigLIP, and most ViT-based embedders.
    """
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = image.astype(np.float32) / 255.0
    arr = (arr - mean) / std
    return arr.transpose(2, 0, 1)  # HWC → CHW


def normalize_wd14(image: np.ndarray) -> np.ndarray:
    """Normalize uint8 RGB (H, W, 3) to float32 (1, H, W, 3) for WD14/ONNX.

    WD14 expects NHWC layout, values in [0, 255] as float32 — no mean/std.
    Input is already letter-boxed to model size via resize_pad_square.
    """
    arr = image.astype(np.float32)
    return arr[np.newaxis, ...]  # (1, H, W, 3)


def preprocess_for_wd14(image: np.ndarray, size: int = 448) -> np.ndarray:
    """Full WD14 preprocessing: pad → float32 NHWC."""
    resized = resize_pad_square(image, size)
    return normalize_wd14(resized)


def preprocess_for_clip(image: np.ndarray, size: int = 224) -> np.ndarray:
    """Full CLIP/SigLIP preprocessing: center-crop → CHW ImageNet-normalized NCHW."""
    cropped = resize_center_crop(image, size)
    normalized = normalize_imagenet(cropped)
    return normalized[np.newaxis, ...]  # NCHW


def preprocess_for_florence(image: np.ndarray, size: int = 768) -> np.ndarray:
    """Florence-2 preprocessing: squash-resize to 768² → CHW ImageNet-normalized NCHW.

    Florence-2 resizes directly to a square (do_center_crop = false) and
    normalizes with ImageNet mean/std at 768×768 — distinct from CLIP's
    224² center-crop contract.
    """
    resized = resize_squash(image, size)
    normalized = normalize_imagenet(resized)
    return normalized[np.newaxis, ...]  # NCHW
