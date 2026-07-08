"""CLIP + WD14 label scoring helpers for the classification engine (P18 Phase 2).

Pure scoring functions — no DB access, no image loading. `engine.py` resolves
the DB rows and stored signals; this module only turns them into per-label
probabilities.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np


@lru_cache(maxsize=2048)
def _embed_prompt_cached(prompt: str) -> np.ndarray:
    """Text-embed one classification prompt; cached process-wide by the prompt string.

    Caller must guard that an image embedder is active (`resolve_image_embedder()`
    is not None) before calling this — it re-resolves the embedder on every cache
    miss (cheap: a single ModelRegistry row lookup, see `resolve_image_embedder`),
    the expensive ONNX session itself is cached separately by `session_manager`.
    """
    from photofant.inference.image_embedder import resolve_image_embedder
    from photofant.inference.interfaces import TextEmbedder

    embedder = resolve_image_embedder()
    if embedder is None:
        raise RuntimeError("Image embedder unavailable — caller must guard before calling")
    if not isinstance(embedder, TextEmbedder):
        raise RuntimeError("Active image embedder has no text encoder — cannot score text prompts")
    return embedder.embed_text(prompt)


def _softmax(values: list[float]) -> list[float]:
    if not values:
        return []
    peak = max(values)
    exponents = [math.exp(value - peak) for value in values]
    total = sum(exponents)
    return [exponent / total for exponent in exponents]


def score_labels_clip(image_embedding: np.ndarray, prompts_per_label: list[list[str]]) -> list[float]:
    """Cosine-similarity softmax over one category's labels.

    `prompts_per_label[i]` is the (already-defaulted, non-empty) CLIP prompt
    list for label i. Each label's prompt embeddings are averaged before the
    cosine, then all labels in the category compete via softmax so the result
    sums to 1 within the category.
    """
    cosines: list[float] = []
    for prompts in prompts_per_label:
        prompt_embeddings = [_embed_prompt_cached(prompt) for prompt in prompts]
        mean_embedding = np.mean(prompt_embeddings, axis=0)
        cosines.append(float(np.dot(image_embedding, mean_embedding)))
    return _softmax(cosines)


def score_label_wd14(wd14_tags: list[str] | None, tag_scores: dict[str, float]) -> float | None:
    """Max stored WD14 tag score over a label's configured tags; None if none are stored."""
    if not wd14_tags:
        return None
    matched = [tag_scores[tag] for tag in wd14_tags if tag in tag_scores]
    if not matched:
        return None
    return max(matched)
