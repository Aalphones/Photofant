"""Protocol interfaces for the inference layer.

Every concrete model adapter (WD14, Florence-2, CLIP, etc.) implements exactly
one of these protocols.  The pipeline and job code depend only on these
interfaces — never on concrete implementations.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


class TagScore:
    """Single tag with its confidence score."""

    __slots__ = ("name", "score")

    def __init__(self, name: str, score: float) -> None:
        self.name = name
        self.score = score

    def __repr__(self) -> str:
        return f"TagScore({self.name!r}, {self.score:.3f})"


@runtime_checkable
class Tagger(Protocol):
    """Classifies an image into a ranked list of tags."""

    def tag(self, image: np.ndarray) -> list[TagScore]:
        """Return tags sorted by descending confidence.

        image: uint8 RGB array (H, W, 3).
        """
        ...


@runtime_checkable
class Captioner(Protocol):
    """Generates a natural-language caption for an image."""

    def caption(self, image: np.ndarray, preset: dict) -> str:
        """Return a caption string.

        image: uint8 RGB array (H, W, 3).
        preset: caption_preset.config dict (model-specific keys).
        """
        ...


@runtime_checkable
class Embedder(Protocol):
    """Produces a feature embedding in a shared image/text space (CLIP-style)."""

    def embed(self, image: np.ndarray) -> np.ndarray:
        """Return a 1-D float32 unit-norm image embedding.

        image: uint8 RGB array (H, W, 3).
        """
        ...

    def embed_text(self, text: str) -> np.ndarray:
        """Return a 1-D float32 unit-norm text embedding in the same space.

        Used to embed a free-text query for text→image semantic search.
        """
        ...


@runtime_checkable
class FaceEngine(Protocol):
    """Detects and encodes faces — reserved for P7."""

    def detect(self, image: np.ndarray) -> list[dict]:
        """Return a list of face dicts (bbox, embedding, …)."""
        ...


# ---------------------------------------------------------------------------
# Generative protocols (P9, ADR-002 — torch/diffusers)
# ---------------------------------------------------------------------------


@runtime_checkable
class Upscaler(Protocol):
    """Upscales an image to higher resolution."""

    def upscale(self, image: np.ndarray, params: dict) -> np.ndarray:
        """Return the upscaled image as uint8 RGB array (H', W', 3).

        params: model-specific parameters (scale_factor, tile_size, …).
        """
        ...


@runtime_checkable
class ImageEditor(Protocol):
    """Applies a prompt-guided edit to an image (img2img / Flux-Edit)."""

    def edit(self, image: np.ndarray, prompt: str, params: dict) -> np.ndarray:
        """Return the edited image as uint8 RGB array (H, W, 3).

        params: strength, steps, guidance_scale, seed, …
        """
        ...


@runtime_checkable
class Inpainter(Protocol):
    """Fills a masked region of an image guided by a prompt."""

    def inpaint(
        self, image: np.ndarray, mask: np.ndarray, prompt: str, params: dict
    ) -> np.ndarray:
        """Return the inpainted image as uint8 RGB array (H, W, 3).

        mask: uint8 single-channel array (H, W) — 255 = region to fill.
        params: strength, steps, guidance_scale, seed, …
        """
        ...
