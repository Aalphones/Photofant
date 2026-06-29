"""Generative Engine — torch/transformers model lifecycle for heavy captioners.

Manages loading and unloading of transformers-based models (Qwen2.5-VL, JoyCaption).
One model at a time to respect VRAM limits.

The generative dependency group (torch, transformers, etc.) is optional.
All public methods gracefully degrade when it is not installed.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
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
    """Check whether the generative dependency group (torch + transformers) is importable."""
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
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

    def load_transformers_model(
        self,
        model_id: str,
        model_path: str,
        *,
        model_class_name: str = "AutoModelForCausalLM",
        torch_dtype: str = "float16",
        device: str = "cuda",
        extra_model_kwargs: dict[str, Any] | None = None,
    ) -> tuple[Any, Any]:
        """Load a transformers model + processor pair, evicting any current pipeline.

        Used for heavy captioners (Qwen2.5-VL, JoyCaption) that are pure
        transformers models rather than diffusers pipelines. Returns (model, processor).
        VRAM coordination is the same as for diffusers: one model at a time.
        """
        availability = check_generative_available()
        if availability is not GenerativeAvailability.AVAILABLE:
            raise RuntimeError(
                f"Generative dependencies not available ({availability}). "
                "Install with: uv pip install photofant[generative]"
            )

        import torch
        import transformers

        _set_offline_env()

        dtype_map = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }
        resolved_dtype = dtype_map.get(torch_dtype, torch.float16)

        model_cls = getattr(transformers, model_class_name, None)
        if model_cls is None:
            from transformers import AutoModelForCausalLM
            model_cls = AutoModelForCausalLM

        with self._lock:
            self._evict_locked()

        log.info("Loading transformers model: %s (%s)", model_id, model_class_name)

        model_kwargs: dict[str, Any] = {
            "torch_dtype": resolved_dtype,
            **(extra_model_kwargs or {}),
        }

        model = model_cls.from_pretrained(model_path, **model_kwargs)
        model = model.to(device)
        model.eval()

        from transformers import AutoProcessor
        processor = AutoProcessor.from_pretrained(model_path)

        with self._lock:
            self._current = _PipelineEntry(
                pipeline=(model, processor),
                model_id=model_id,
                pipeline_type=f"transformers:{model_class_name}",
            )

        log.info("Transformers model ready: %s", model_id)
        return model, processor

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

        import gc

        model_id = self._current.model_id
        del self._current.pipeline
        self._current = None

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        gc.collect()
        log.info("Evicted generative pipeline: %s", model_id)

generative_engine = GenerativeEngine()
