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
