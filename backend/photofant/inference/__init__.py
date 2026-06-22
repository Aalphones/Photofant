"""Inference layer — ONNX-based model adapters, generative engine, and session lifecycle."""
from __future__ import annotations

from photofant.inference.generative_engine import generative_engine
from photofant.inference.interfaces import (
    Captioner,
    Embedder,
    FaceEngine,
    ImageEditor,
    Inpainter,
    Tagger,
    TagScore,
    Upscaler,
)
from photofant.inference.session_manager import session_manager

__all__ = [
    "Captioner",
    "Embedder",
    "FaceEngine",
    "ImageEditor",
    "Inpainter",
    "TagScore",
    "Tagger",
    "Upscaler",
    "generative_engine",
    "session_manager",
]
