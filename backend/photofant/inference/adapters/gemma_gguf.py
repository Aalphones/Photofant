"""GGUF Gemma adapter — llama.cpp runtime, 2nd `TextGenerator` behind the same
capability (ADR-029, extends ADR-028 without revoking it).

Second runtime alongside `inference/adapters/gemma.py` (torch/transformers). Same
`TextGenerator` contract — the routing layer (Phase 2, `capabilities.py`) picks this
adapter over the torch one by the bound model's manifest `format`. Callers never
know which runtime backs the capability.

Gemma's chat template has no `system` role — folded into the user turn, same
convention as the torch adapter.

Vision-Naht: `GemmaGgufVisionAdapter` additionally satisfies `VisionTextGenerator`
(structural, class-based — same pattern as `TextEmbedder`/`Embedder`, see
`clip.py`/`dinov2.py`). It is only instantiated when a `mmproj` component is bound;
a plain `GemmaGgufAdapter` has no `generate_with_image` method at all, so
`isinstance(gen, VisionTextGenerator)` reflects the bind, not just a runtime flag.
"""
from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from PIL import Image as PILImage

if TYPE_CHECKING:
    from photofant.inference.gguf_engine import GgufEngine

log = logging.getLogger(__name__)


class GemmaGgufAdapter:
    """`TextGenerator` backed by a GGUF Gemma model via llama.cpp."""

    def __init__(self, manifest_id: str, model_path: str, mmproj_path: str | None = None) -> None:
        self._manifest_id = manifest_id
        self._model_path = str(Path(model_path))
        self._mmproj_path = str(Path(mmproj_path)) if mmproj_path else None

    @property
    def model_id(self) -> str:
        return self._manifest_id

    def generate(self, prompt: str, *, system: str | None = None, max_new_tokens: int = 512) -> str:
        from photofant.inference.gguf_engine import check_gguf_available, gguf_engine

        if check_gguf_available().value != "available":
            log.warning("GGUF dependencies not available — skipping GGUF Gemma generation")
            return ""

        llama = self._load(gguf_engine)

        # Gemma's chat template rejects a "system" role — fold into the user turn,
        # same convention as the torch adapter (gemma.py).
        user_text = prompt if not system else f"{system}\n\n{prompt}"
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_text}]

        completion = llama.create_chat_completion(messages=messages, max_tokens=max_new_tokens)
        text: str = completion["choices"][0]["message"]["content"] or ""
        return text.strip()

    def _load(self, gguf_engine: GgufEngine) -> Any:
        return gguf_engine.load(
            model_id=self._manifest_id,
            model_path=self._model_path,
            mmproj_path=self._mmproj_path,
        )


class GemmaGgufVisionAdapter(GemmaGgufAdapter):
    """`GemmaGgufAdapter` extended with `VisionTextGenerator.generate_with_image`.

    Only instantiated by `resolve_gemma_gguf` when a `mmproj` component is bound.
    Whether the vision *call* actually works still depends on llama-cpp-python
    carrying a Gemma-3 vision chat handler (README risk) — `gguf_engine.has_vision`
    gates the call itself; the Naht (this class + protocol) stays correct either way.
    """

    def __init__(self, manifest_id: str, model_path: str, mmproj_path: str) -> None:
        super().__init__(manifest_id, model_path, mmproj_path)

    def generate_with_image(
        self, image: np.ndarray, prompt: str, *, system: str | None = None, max_new_tokens: int = 512
    ) -> str:
        from photofant.inference.gguf_engine import check_gguf_available, gguf_engine

        if check_gguf_available().value != "available":
            log.warning("GGUF dependencies not available — skipping GGUF Gemma vision generation")
            return ""

        llama = self._load(gguf_engine)
        if not gguf_engine.has_vision:
            raise RuntimeError(
                "Kein Vision-Handler geladen — llama-cpp-python unterstützt Gemma-3-Vision "
                "in dieser Version nicht (mmproj ist gebunden, siehe ADR-029/README-Risiko)"
            )

        image_data_uri = _encode_image_data_uri(image)
        user_text = prompt if not system else f"{system}\n\n{prompt}"
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                    {"type": "text", "text": user_text},
                ],
            }
        ]

        completion = llama.create_chat_completion(messages=messages, max_tokens=max_new_tokens)
        text: str = completion["choices"][0]["message"]["content"] or ""
        return text.strip()


def _encode_image_data_uri(image: np.ndarray) -> str:
    """Encode a uint8 RGB array as a base64 PNG data URI (llama.cpp vision handler input)."""
    buffer = io.BytesIO()
    PILImage.fromarray(image).save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def resolve_gemma_gguf(manifest_id: str) -> GemmaGgufAdapter | None:
    """Return a GemmaGgufAdapter if *manifest_id* is enabled+bound; None otherwise.

    Mirrors `resolve_gemma`: reads the DB registry for the on-disk model path; a
    disabled or unbound model degrades gracefully to None. The optional `mmproj`
    component (Vision-Naht) rides the same `components` JSON column used by other
    multi-file models (e.g. Flux) — absent for a text-only bind, in which case a
    plain `GemmaGgufAdapter` is returned instead of the vision subclass.
    """
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        entry = (
            session.query(ModelRegistry)
            .filter_by(manifest_id=manifest_id, enabled=True)
            .first()
        )
        if entry is None or not entry.path:
            log.debug("GGUF Gemma model %r not enabled or has no path — skipping", manifest_id)
            return None
        model_path = entry.path
        mmproj_path = (entry.components or {}).get("mmproj")

    if mmproj_path:
        return GemmaGgufVisionAdapter(manifest_id=manifest_id, model_path=model_path, mmproj_path=mmproj_path)
    return GemmaGgufAdapter(manifest_id=manifest_id, model_path=model_path)
