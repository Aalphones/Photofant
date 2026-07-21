"""GGUF Runtime — llama.cpp model lifecycle for the local GGUF Gemma (ADR-029).

Second inference runtime alongside `GenerativeEngine` (torch/transformers, ADR-028).
Mirrors its **form** — lazy-load, one model resident, idle-unload, `threading.Lock`,
a `last_used`-tracked entry — but not its content: llama.cpp has its own object
lifecycle (`Llama`), no torch device/dtype handling.

The gemma-gguf dependency group (`llama-cpp-python`) is optional. All public methods
gracefully degrade when it is not installed.

VRAM-Invariante (ADR-029): genau ein Heavy-Modell resident über **beide** Runtimes.
Durchgesetzt per gegenseitigem Cross-Unload — `load()` hier evict't zuerst den
torch-Slot (`generative_engine.unload()`); der torch-Slot evict't umgekehrt diesen
hier (siehe `generative_engine.load_transformers_model`).
"""
from __future__ import annotations

import importlib.util
import logging
import os
import shutil
import site
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

IDLE_TIMEOUT_SECONDS: float = 120.0

# Guards the one-time CUDA-runtime provisioning below.
_cuda_runtime_provisioned = False


def _find_llama_cpp_lib_dir() -> Path | None:
    """Locate llama-cpp-python's native `lib/` folder without importing it.

    Importing llama_cpp is exactly what triggers the DLL load we are trying to
    fix up first, so we resolve the path via the import machinery instead
    (`find_spec` does not execute the module).
    """
    spec = importlib.util.find_spec("llama_cpp")
    if spec is None or spec.origin is None:
        return None
    lib_dir = Path(spec.origin).parent / "lib"
    return lib_dir if lib_dir.is_dir() else None


def _nvidia_bin_dirs() -> list[Path]:
    """Every `nvidia/*/bin` folder shipped by the `nvidia-*-cu12` wheels.

    Discovered from the live `site-packages` (never a hardcoded path, so it
    travels to any machine/venv). `sys.prefix` is added as a fallback because a
    venv's own site-packages is not always in `site.getsitepackages()`.
    """
    site_dirs: list[str] = list(site.getsitepackages())
    user_site = site.getusersitepackages()
    if user_site:
        site_dirs.append(user_site)
    site_dirs.append(str(Path(sys.prefix) / "Lib" / "site-packages"))

    bin_dirs: list[Path] = []
    seen: set[str] = set()
    for site_dir in site_dirs:
        nvidia_root = Path(site_dir) / "nvidia"
        if not nvidia_root.is_dir():
            continue
        for bin_dir in nvidia_root.glob("*/bin"):
            resolved = str(bin_dir.resolve())
            if bin_dir.is_dir() and resolved not in seen:
                seen.add(resolved)
                bin_dirs.append(bin_dir)
    return bin_dirs


def _provision_cuda_runtime_dlls() -> None:
    """Place the CUDA-12 runtime DLLs next to llama-cpp's `ggml-cuda.dll`.

    The CUDA build of llama-cpp-python links `ggml-cuda.dll` against
    `cudart64_12.dll` / `cublas64_12.dll`, but ships neither. A torch install
    would drag them in; this backend carries no torch, so without help
    `ggml-cuda.dll` fails to load and the whole import degrades to a silent
    "not available".

    The Windows loader resolves a DLL's dependencies from the directory of the
    DLL being loaded — for `ggml-cuda.dll` that is llama-cpp's `lib/`. It does
    NOT consult `PATH`, `os.add_dll_directory`, or already-loaded modules here
    (llama-cpp loads with a full path and no user-dir search flag), so the only
    reliable fix is to have the DLLs physically sit in that `lib/`. We hardlink
    them from the `nvidia-*-cu12` wheels (same volume → zero extra space; a copy
    is the cross-volume fallback). Idempotent and self-healing: a llama-cpp
    reinstall wipes `lib/`, and the next import re-links.

    No-op off Windows: there `.so` resolution runs through the wheels' RPATH and
    `os.link` semantics differ — the CUDA linux wheels are found without help.
    """
    global _cuda_runtime_provisioned
    if _cuda_runtime_provisioned:
        return
    _cuda_runtime_provisioned = True

    if os.name != "nt":
        return

    lib_dir = _find_llama_cpp_lib_dir()
    if lib_dir is None:
        return

    for bin_dir in _nvidia_bin_dirs():
        for source_dll in bin_dir.glob("*.dll"):
            target_dll = lib_dir / source_dll.name
            if target_dll.exists():
                continue
            try:
                os.link(source_dll, target_dll)
            except OSError:
                # Cross-volume or hardlink-unsupported filesystem — fall back to
                # a plain copy so the DLL is still resolvable next to ggml-cuda.
                try:
                    shutil.copy2(source_dll, target_dll)
                except OSError:
                    log.warning("Could not provision CUDA runtime DLL %s", source_dll.name, exc_info=True)
                    continue
            log.debug("Provisioned CUDA runtime DLL into llama_cpp/lib: %s", source_dll.name)


class GgufAvailability(StrEnum):
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    IMPORT_ERROR = "import_error"


@dataclass
class _GgufEntry:
    llama: Any
    model_id: str
    has_vision: bool
    mmproj_path: str | None
    last_used: float = field(default_factory=time.monotonic)


def check_gguf_available() -> GgufAvailability:
    """Check whether llama-cpp-python (the gemma-gguf extra) is importable."""
    _provision_cuda_runtime_dlls()
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return GgufAvailability.NOT_INSTALLED
    except Exception:
        return GgufAvailability.IMPORT_ERROR
    return GgufAvailability.AVAILABLE


def _build_vision_chat_handler(mmproj_path: str) -> Any | None:
    """Build the Gemma-3-vision chat handler for llama-cpp-python, or None if unsupported.

    The concrete handler class is version-dependent (README risk: llama-cpp-python
    may not ship a Gemma-3 handler yet, only LLaVA-family ones). Missing it degrades
    to plain text — the Vision-Naht stays correct, only the vision switch waits on
    library support (see Smoke-Checkliste #6).
    """
    try:
        from llama_cpp.llama_chat_format import Gemma3ChatHandler  # type: ignore[import-not-found]
    except ImportError:
        log.warning(
            "llama-cpp-python has no Gemma3ChatHandler in this version — mmproj bound "
            "but ignored, falling back to text-only (Vision-Naht waits on library support)"
        )
        return None

    try:
        return Gemma3ChatHandler(clip_model_path=mmproj_path)
    except Exception:
        log.warning("Failed to construct Gemma3ChatHandler with mmproj=%s", mmproj_path, exc_info=True)
        return None


class GgufEngine:
    """Thread-safe, single-model manager for llama.cpp GGUF models.

    VRAM budget: shares the app's one-heavy-model invariant with `GenerativeEngine`
    via cross-unload (ADR-029) — loading a GGUF model evicts any resident torch
    pipeline first, and vice versa.
    """

    def __init__(self, idle_timeout: float = IDLE_TIMEOUT_SECONDS) -> None:
        self._idle_timeout = idle_timeout
        self._lock = threading.Lock()
        self._current: _GgufEntry | None = None

    @property
    def loaded_model_id(self) -> str | None:
        with self._lock:
            if self._current is None:
                return None
            return self._current.model_id

    @property
    def has_vision(self) -> bool:
        """Whether the resident model has a working vision chat handler attached."""
        with self._lock:
            return self._current is not None and self._current.has_vision

    def load(
        self,
        model_id: str,
        model_path: str,
        *,
        mmproj_path: str | None = None,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
    ) -> Any:
        """Load a GGUF model, evicting the torch slot and any current GGUF model first.

        `mmproj_path` is the optional vision-projector companion file (Vision-Naht,
        README §Vision-Naht) — when set, the model is constructed with the matching
        vision chat handler; when the handler is unavailable or `mmproj_path` is
        None, it loads text-only. Returns the `Llama` instance.

        Reuses the resident model when both *model_id* and *mmproj_path* already
        match — every adapter calls this on each `generate`, and reloading a
        4-12B GGUF from disk per call would otherwise dominate request latency
        for no reason (mirrors the same fix in `GenerativeEngine`).
        """
        availability = check_gguf_available()
        if availability is not GgufAvailability.AVAILABLE:
            raise RuntimeError(
                f"GGUF dependencies not available ({availability}). "
                "Install with: uv pip install 'photofant[gemma-gguf]'"
            )

        with self._lock:
            if (
                self._current is not None
                and self._current.model_id == model_id
                and self._current.mmproj_path == mmproj_path
            ):
                self._current.last_used = time.monotonic()
                log.debug("Reusing resident GGUF model: %s", model_id)
                return self._current.llama

        # Cross-unload (ADR-029): exactly one heavy model resident across BOTH
        # runtimes — evict the torch slot before this one takes VRAM. Lazy import
        # against the import cycle (generative_engine imports this module back).
        from photofant.inference.generative_engine import generative_engine
        generative_engine.unload()

        with self._lock:
            self._evict_locked()

        chat_handler = _build_vision_chat_handler(mmproj_path) if mmproj_path else None
        has_vision = chat_handler is not None

        from llama_cpp import Llama

        log.info("Loading GGUF model: %s (mmproj=%s)", model_id, bool(mmproj_path))

        llama_kwargs: dict[str, Any] = {
            "model_path": str(Path(model_path)),
            "n_ctx": n_ctx,
            "n_gpu_layers": n_gpu_layers,
            # llama.cpp logs "offloaded N/N layers to GPU" at this verbosity — the
            # signal Smoke-Checkliste #1 reads to confirm CUDA offload (not CPU fallback).
            "verbose": True,
        }
        if chat_handler is not None:
            llama_kwargs["chat_handler"] = chat_handler

        llama = Llama(**llama_kwargs)

        with self._lock:
            self._current = _GgufEntry(
                llama=llama, model_id=model_id, has_vision=has_vision, mmproj_path=mmproj_path
            )

        log.info("GGUF model ready: %s", model_id)
        return llama

    def unload(self) -> None:
        """Explicitly unload the current model and free VRAM."""
        with self._lock:
            self._evict_locked()

    def evict_idle(self, idle_timeout: float | None = None) -> None:
        """Evict the model if it has been idle longer than the timeout.

        `idle_timeout` overrides the instance default per call — the app's idle
        loop passes `ai.idleTimeoutSeconds`, same as `GenerativeEngine.evict_idle`.
        """
        timeout = self._idle_timeout if idle_timeout is None else idle_timeout
        now = time.monotonic()
        with self._lock:
            if self._current is None:
                return
            if (now - self._current.last_used) > timeout:
                log.info(
                    "Evicting idle GGUF model: %s (idle %.0fs)",
                    self._current.model_id,
                    now - self._current.last_used,
                )
                self._evict_locked()

    def _evict_locked(self) -> None:
        """Evict current model — caller must hold self._lock."""
        if self._current is None:
            return

        import gc

        model_id = self._current.model_id
        del self._current.llama
        self._current = None
        gc.collect()
        log.info("Evicted GGUF model: %s", model_id)


gguf_engine = GgufEngine()
