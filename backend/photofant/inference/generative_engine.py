"""Generative Engine — torch/diffusers pipeline lifecycle (ADR-002).

Manages loading and unloading of generative AI models (Upscale, Flux-Edit,
Inpainting, heavy Captioners). One pipeline at a time to respect VRAM limits.
Coordinates with the ONNX SessionManager: evicts idle ONNX sessions before
loading a large torch model.

The generative dependency group (torch, diffusers, etc.) is optional.
All public methods gracefully degrade when it is not installed.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

IDLE_TIMEOUT_SECONDS: float = 120.0


class GenerativeAvailability(StrEnum):
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    IMPORT_ERROR = "import_error"


@dataclass
class _PipelineEntry:
    pipeline: Any
    model_id: str
    pipeline_type: str
    last_used: float = field(default_factory=time.monotonic)


def check_generative_available() -> GenerativeAvailability:
    """Check whether the generative dependency group is importable."""
    try:
        import diffusers  # noqa: F401
        import torch  # noqa: F401
    except ImportError:
        return GenerativeAvailability.NOT_INSTALLED
    except Exception:
        return GenerativeAvailability.IMPORT_ERROR
    return GenerativeAvailability.AVAILABLE


def _set_offline_env() -> None:
    """Enforce offline mode for HuggingFace libraries (Konzept §1)."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


class GenerativeEngine:
    """Thread-safe, single-pipeline manager for torch/diffusers models.

    VRAM budget: one generative pipeline loaded at a time.
    Loading a new pipeline evicts the current one first.
    """

    def __init__(self, idle_timeout: float = IDLE_TIMEOUT_SECONDS) -> None:
        self._idle_timeout = idle_timeout
        self._lock = threading.Lock()
        self._current: _PipelineEntry | None = None

    @property
    def loaded_model_id(self) -> str | None:
        with self._lock:
            if self._current is None:
                return None
            return self._current.model_id

    def load_pipeline(
        self,
        model_id: str,
        pipeline_class_name: str,
        *,
        model_path: str | None = None,
        components: dict[str, str] | None = None,
        torch_dtype: str = "float16",
        device: str = "cuda",
        extra_kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Load a diffusers pipeline, evicting any currently loaded model.

        Args:
            model_id: Registry identifier (for tracking).
            pipeline_class_name: diffusers class name, e.g. 'FluxPipeline'.
            model_path: Path to a single model directory (diffusers layout).
            components: Map of component names to paths for component models
                        (e.g. {"transformer": "...", "text_encoder": "...", "vae": "..."}).
            torch_dtype: Weight precision — "float16", "bfloat16", or "float32".
            device: Target device.
            extra_kwargs: Additional kwargs passed to from_pretrained.
        """
        availability = check_generative_available()
        if availability is not GenerativeAvailability.AVAILABLE:
            raise RuntimeError(
                f"Generative dependencies not available ({availability}). "
                "Install with: uv pip install photofant[generative]"
            )

        import diffusers
        import torch

        _set_offline_env()

        dtype_map = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }
        resolved_dtype = dtype_map.get(torch_dtype, torch.float16)

        pipeline_cls = getattr(diffusers, pipeline_class_name, None)
        if pipeline_cls is None:
            raise ValueError(f"Unknown diffusers pipeline class: {pipeline_class_name}")

        with self._lock:
            self._evict_locked()

        log.info("Loading generative pipeline: %s (%s)", model_id, pipeline_class_name)

        kwargs: dict[str, Any] = {
            "torch_dtype": resolved_dtype,
            **(extra_kwargs or {}),
        }

        if components:
            pipeline = self._load_component_model(
                pipeline_cls, components, device, kwargs
            )
        elif model_path:
            pipeline = pipeline_cls.from_pretrained(model_path, **kwargs)
            pipeline = pipeline.to(device)
        else:
            raise ValueError("Either model_path or components must be provided")

        with self._lock:
            self._current = _PipelineEntry(
                pipeline=pipeline,
                model_id=model_id,
                pipeline_type=pipeline_class_name,
            )

        log.info("Generative pipeline ready: %s", model_id)
        return pipeline

    def get_pipeline(self) -> Any | None:
        """Return the currently loaded pipeline, updating last-used timestamp."""
        with self._lock:
            if self._current is None:
                return None
            self._current.last_used = time.monotonic()
            return self._current.pipeline

    def unload(self) -> None:
        """Explicitly unload the current pipeline and free VRAM."""
        with self._lock:
            self._evict_locked()

    def evict_idle(self) -> None:
        """Evict the pipeline if it has been idle longer than the timeout."""
        now = time.monotonic()
        with self._lock:
            if self._current is None:
                return
            if (now - self._current.last_used) > self._idle_timeout:
                log.info(
                    "Evicting idle generative pipeline: %s (idle %.0fs)",
                    self._current.model_id,
                    now - self._current.last_used,
                )
                self._evict_locked()

    def _evict_locked(self) -> None:
        """Evict current pipeline — caller must hold self._lock."""
        if self._current is None:
            return

        model_id = self._current.model_id
        del self._current.pipeline
        self._current = None

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        log.info("Evicted generative pipeline: %s", model_id)

    def _load_component_model(
        self,
        pipeline_cls: type,
        components: dict[str, str],
        device: str,
        kwargs: dict[str, Any],
    ) -> Any:
        """Load a pipeline from separately stored components (Konzept §12.1)."""
        import diffusers  # noqa: F811

        main_path = components.get("diffusion") or components.get("transformer")
        if main_path is None:
            raise ValueError(
                "Component model requires at least a 'diffusion' or 'transformer' path"
            )

        component_kwargs: dict[str, Any] = {}

        for component_name, component_path in components.items():
            if component_name in ("diffusion", "transformer"):
                continue
            resolved_path = Path(component_path)
            if not resolved_path.exists():
                raise FileNotFoundError(
                    f"Component '{component_name}' not found at: {component_path}"
                )

            if component_name == "text_encoder":
                from transformers import CLIPTextModel
                component_kwargs["text_encoder"] = CLIPTextModel.from_pretrained(
                    str(resolved_path), **kwargs
                )
            elif component_name == "vae":
                vae_cls = getattr(diffusers, "AutoencoderKL", None)
                if vae_cls is not None:
                    component_kwargs["vae"] = vae_cls.from_pretrained(
                        str(resolved_path), **kwargs
                    )

        pipeline = pipeline_cls.from_pretrained(
            main_path,
            **component_kwargs,
            **kwargs,
        )
        return pipeline.to(device)


generative_engine = GenerativeEngine()
