"""GPU VRAM detection and variant recommendation (Konzept §12.4)."""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpuInfo:
    name: str
    vram_bytes: int
    vram_gb: float


def detect_gpu() -> GpuInfo | None:
    """Detect the primary GPU and its VRAM.

    Tries torch first (most accurate when the generative group is installed),
    falls back to nvidia-smi CLI parsing.
    """
    info = _try_torch()
    if info is not None:
        return info
    return _try_nvidia_smi()


def _try_torch() -> GpuInfo | None:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return None

    if not torch.cuda.is_available():
        return None

    try:
        props = torch.cuda.get_device_properties(0)
        vram_bytes = props.total_mem
        return GpuInfo(
            name=props.name,
            vram_bytes=vram_bytes,
            vram_gb=round(vram_bytes / (1024**3), 1),
        )
    except Exception:  # noqa: BLE001
        log.debug("torch.cuda.get_device_properties failed", exc_info=True)
        return None


def _try_nvidia_smi() -> GpuInfo | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        line = result.stdout.strip().split("\n")[0]
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 2:
            return None
        name = parts[0]
        vram_mib = float(parts[1])
        vram_bytes = int(vram_mib * 1024 * 1024)
        return GpuInfo(
            name=name,
            vram_bytes=vram_bytes,
            vram_gb=round(vram_bytes / (1024**3), 1),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return None
    except Exception:  # noqa: BLE001
        log.debug("nvidia-smi detection failed", exc_info=True)
        return None


def suggest_tagging_workers(vram_gb: float) -> int:
    """Suggest how many parallel WD14 tagging workers fit into the given VRAM.

    WD14 SwinV2-v3: ~450 MB per session instance + ~200 MB activations per run.
    """
    available_gb = vram_gb - 1.5  # OS + other models
    return max(1, min(4, int(available_gb / 0.65)))


def suggest_captioning_workers(vram_gb: float) -> int:
    """Suggest how many parallel Florence-2 captioning workers fit into the given VRAM.

    Florence-2-base: ~1.5 GB per session instance (4 ONNX sessions) + ~300 MB activations.
    """
    available_gb = vram_gb - 0.5  # OS
    return max(1, min(4, int(available_gb / 1.8)))


def recommend_variant(
    vram_gb: float | None,
    variants: list[dict[str, Any]],
) -> str | None:
    """Recommend the best variant for the detected VRAM.

    Returns the variant name that fits, preferring higher quality (bf16 > fp8 > gguf).
    Returns None if no VRAM info is available.
    """
    if vram_gb is None or not variants:
        return None

    for variant in variants:
        required_vram = variant.get("vram_gb")
        if required_vram is not None and vram_gb >= required_vram:
            return variant.get("name")

    last_variant = variants[-1]
    return last_variant.get("name")
