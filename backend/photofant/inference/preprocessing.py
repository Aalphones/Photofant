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


def resize_center_crop(image: np.ndarray, size: int, crop_size: int | None = None) -> np.ndarray:
    """Resize shortest side to `size`, then center-crop to (crop_size, crop_size).

    image: uint8 RGB (H, W, 3).
    crop_size defaults to `size` (CLIP: resize 224 → crop 224). DINOv2 needs them
    to differ — resize shortest edge to 256, then crop 224 — so it passes crop_size.
    Returns uint8 RGB (crop_size, crop_size, 3).
    """
    from PIL import Image as PILImage

    crop = crop_size if crop_size is not None else size
    pil = PILImage.fromarray(image).convert("RGB")
    original_width, original_height = pil.size
    scale = size / min(original_width, original_height)
    new_width = round(original_width * scale)
    new_height = round(original_height * scale)
    pil = pil.resize((new_width, new_height), PILImage.LANCZOS)
    left = (new_width - crop) // 2
    top = (new_height - crop) // 2
    pil = pil.crop((left, top, left + crop, top + crop))
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
    Used by Florence-2 and most ViT-based models. CLIP and SigLIP each ship
    their own stats (`normalize_clip` / `normalize_siglip`) — don't use this for them.
    """
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = image.astype(np.float32) / 255.0
    arr = (arr - mean) / std
    return arr.transpose(2, 0, 1)  # HWC → CHW


def normalize_clip(image: np.ndarray) -> np.ndarray:
    """Normalize uint8 RGB (H, W, 3) to float32 (3, H, W) with CLIP's own stats.

    CLIP does NOT use ImageNet mean/std — it ships its own (OpenAI CLIP) values.
    Used by the CLIP image encoder only; SigLIP uses `normalize_siglip`.
    """
    mean = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
    std = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)
    arr = image.astype(np.float32) / 255.0
    arr = (arr - mean) / std
    return arr.transpose(2, 0, 1)  # HWC → CHW


def normalize_siglip(image: np.ndarray) -> np.ndarray:
    """Normalize uint8 RGB (H, W, 3) to float32 (3, H, W) with SigLIP's stats.

    SigLIP2 uses mean/std 0.5 on every channel — a plain rescale to [-1, 1] —
    NOT CLIP's or ImageNet's stats. Verify against the model's
    preprocessor_config.json (`image_mean` / `image_std`) after download.
    """
    mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    std = np.array([0.5, 0.5, 0.5], dtype=np.float32)
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
    """Full CLIP preprocessing: 224² center-crop → CLIP-normalized NCHW."""
    cropped = resize_center_crop(image, size)
    normalized = normalize_clip(cropped)
    return normalized[np.newaxis, ...]  # NCHW


def preprocess_for_siglip(image: np.ndarray, size: int = 384) -> np.ndarray:
    """Full SigLIP2 preprocessing: squash-resize to size² → [-1,1]-normalized NCHW.

    SigLIP2 resizes directly to a square (do_center_crop = false) at 384×384 and
    normalizes with mean/std 0.5 — distinct from CLIP's 224² center-crop contract.
    Verify size + resize mode against the model's preprocessor_config.json after download.
    """
    resized = resize_squash(image, size)
    normalized = normalize_siglip(resized)
    return normalized[np.newaxis, ...]  # NCHW


def preprocess_for_dinov2(image: np.ndarray, size: int = 256, crop_size: int = 224) -> np.ndarray:
    """Full DINOv2 preprocessing: resize shortest edge to 256 → center-crop 224² → ImageNet NCHW.

    Verified against facebook/dinov2-with-registers-base preprocessor_config.json:
    resize shortest edge to 256 (bicubic), center-crop 224×224, rescale 1/255, then
    ImageNet mean/std — the same stats as Florence, but with a 256→224 resize-then-crop
    step (SigLIP squashes to 384² with 0.5-stats; the contracts must not be mixed).
    """
    cropped = resize_center_crop(image, size, crop_size)
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
