"""Protocol interfaces for the inference layer.

Every concrete model adapter (WD14, Florence-2, CLIP, etc.) implements exactly
one of these protocols. The pipeline and job code depend only on these
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
    """Produces a feature embedding from an image.

    Image-only by contract — text is NOT part of this protocol. A visual model
    like DINOv2 (P37, role "visual_rerank") embeds images but has no text encoder;
    it satisfies `Embedder` and nothing more. Models that also map text into the
    same space (CLIP, SigLIP2) satisfy the richer `TextEmbedder` below. Callers
    that need a text query check the capability (`isinstance(x, TextEmbedder)`)
    instead of calling `embed_text` blindly.
    """

    @property
    def dim(self) -> int:
        """Dimensionality of the vectors this embedder produces (e.g. 768, 1024).

        The vector index is typed to one dimension; the resolver's startup guard
        compares this against it so a model swap that changes the dimension is
        caught loudly instead of corrupting the index.
        """
        ...

    def embed(self, image: np.ndarray) -> np.ndarray:
        """Return a 1-D float32 unit-norm image embedding.

        image: uint8 RGB array (H, W, 3).
        """
        ...


@runtime_checkable
class TextEmbedder(Embedder, Protocol):
    """An `Embedder` that also maps free text into the same space (CLIP-style).

    Backs text→image semantic search: a text query and an image become comparable
    by cosine similarity because both land in one shared space. CLIP and SigLIP2
    satisfy this; a purely visual embedder (DINOv2) does not.
    """

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


@runtime_checkable
class TextGenerator(Protocol):
    """Generates text from a prompt — the LLM contract for the AI layer (P27).

    Text-only by design (no image). Concrete adapters (Gemma) ride the shared
    generative model lifecycle. Jobs never depend on a concrete generator; they
    request a `Capability` and get one of these back.
    """

    @property
    def model_id(self) -> str:
        """The manifest id of the backing model — for the explainability payload."""
        ...

    def generate(self, prompt: str, *, system: str | None = None, max_new_tokens: int = 512) -> str:
        """Return generated text. `system` is an optional instruction prepended to the turn."""
        ...
