"""Inference layer — ONNX-based model adapters, generative engine, and session lifecycle."""
from __future__ import annotations

from photofant.inference.interfaces import (
    Captioner,
    Embedder,
    FaceEngine,
    Tagger,
    TagScore,
)
from photofant.inference.session_manager import session_manager

__all__ = [
    "Captioner",
    "Embedder",
    "FaceEngine",
    "TagScore",
    "Tagger",
    "session_manager",
]
