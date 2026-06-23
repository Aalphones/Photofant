"""SeedVR2 upscaler wrapper (Konzept §12.3/§12.4, ADR-002 Phase 3).

SeedVR2 has no official diffusers pipeline. This module tries three loading
strategies in order:
  1. Official ``seedvr2`` package (if/when the community releases one).
  2. ``spandrel`` — a generic super-resolution model loader that handles
     safetensors/pth weights for ESRGAN, SRFormer and similar architectures.
     SeedVR2 weights are DiT-based, but spandrel may gain support in future.
  3. PIL Lanczos — a quality-preserving software fallback so the job never
     silently fails; logged as a warning so the user knows GPU was not used.

VRAM coordination: always call ``generative_engine.unload()`` before loading
so that Flux/other pipelines don't compete for GPU memory.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

log = logging.getLogger(__name__)

_DEFAULT_SCALE = 4


class SeedVR2Upscaler:
    """Wraps SeedVR2 inference behind a stable ``upscale(image, scale)`` API."""

    def __init__(self, model_path: str) -> None:
        self._model_path = Path(model_path)
        if not self._model_path.exists():
            raise FileNotFoundError(f"SeedVR2 model not found: {model_path}")
        self._model: object | None = None
        self._backend: str = "none"

    def load(self) -> None:
        """Load model weights; must be called before ``upscale()``."""
        if self._try_seedvr2():
            return
        if self._try_spandrel():
            return
        log.warning(
            "SeedVR2: neither 'seedvr2' nor 'spandrel' package available — "
            "will fall back to PIL Lanczos. Install one for GPU upscaling."
        )
        self._backend = "pil"

    def upscale(self, image: "PILImage.Image", scale: int = _DEFAULT_SCALE) -> "PILImage.Image":
        """Upscale PIL image by ``scale`` factor."""
        if self._backend == "seedvr2":
            return self._run_seedvr2(image, scale)
        if self._backend == "spandrel":
            return self._run_spandrel(image, scale)
        return self._run_pil(image, scale)

    def unload(self) -> None:
        """Release GPU memory."""
        self._model = None
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        import gc
        gc.collect()
        log.info("SeedVR2Upscaler unloaded (%s backend)", self._backend)

    # ── Loading strategies ────────────────────────────────────────────────────

    def _try_seedvr2(self) -> bool:
        try:
            import seedvr2  # type: ignore[import-not-found]  # noqa: F401
            from seedvr2.pipeline import SeedVR2Pipeline  # type: ignore[import-not-found]
            self._model = SeedVR2Pipeline.from_pretrained(str(self._model_path))
            self._backend = "seedvr2"
            log.info("SeedVR2Upscaler: loaded via seedvr2 package from %s", self._model_path)
            return True
        except ImportError:
            return False
        except Exception:
            log.debug("seedvr2 package found but loading failed", exc_info=True)
            return False

    def _try_spandrel(self) -> bool:
        try:
            from spandrel import ImageModelDescriptor, ModelLoader  # type: ignore[import-not-found]
            loader = ModelLoader()
            descriptor = loader.load_from_file(str(self._model_path))
            if not isinstance(descriptor, ImageModelDescriptor):
                log.debug("spandrel loaded a non-image-model descriptor; skipping")
                return False
            self._model = descriptor
            self._backend = "spandrel"
            log.info("SeedVR2Upscaler: loaded via spandrel from %s", self._model_path)
            return True
        except ImportError:
            return False
        except Exception:
            log.debug("spandrel loading failed", exc_info=True)
            return False

    # ── Inference ─────────────────────────────────────────────────────────────

    def _run_seedvr2(self, image: "PILImage.Image", scale: int) -> "PILImage.Image":
        from seedvr2.pipeline import SeedVR2Pipeline  # type: ignore[import-not-found]
        pipeline: SeedVR2Pipeline = self._model  # type: ignore[assignment]
        result = pipeline(image, upscale_factor=scale)
        return result.images[0] if hasattr(result, "images") else result

    def _run_spandrel(self, image: "PILImage.Image", scale: int) -> "PILImage.Image":
        import numpy as np
        import torch
        from spandrel import ImageModelDescriptor  # type: ignore[import-not-found]

        descriptor: ImageModelDescriptor = self._model  # type: ignore[assignment]
        device = "cuda" if torch.cuda.is_available() else "cpu"
        descriptor.model.to(device).eval()

        np_image = np.array(image.convert("RGB")).astype(np.float32) / 255.0
        tensor = torch.from_numpy(np_image).permute(2, 0, 1).unsqueeze(0).to(device)

        with torch.no_grad():
            output = descriptor(tensor)

        output_np = output.squeeze(0).permute(1, 2, 0).cpu().numpy()
        output_np = (output_np.clip(0, 1) * 255).astype(np.uint8)

        from PIL import Image
        result = Image.fromarray(output_np)

        # If the model's native scale doesn't match, resize to requested scale
        target_w = image.width * scale
        target_h = image.height * scale
        if result.size != (target_w, target_h):
            result = result.resize((target_w, target_h), Image.Resampling.LANCZOS)
        return result

    def _run_pil(self, image: "PILImage.Image", scale: int) -> "PILImage.Image":
        from PIL import Image
        target_w = image.width * scale
        target_h = image.height * scale
        return image.resize((target_w, target_h), Image.Resampling.LANCZOS)
