"""DINOv2 ViT-B/14 (with registers) embedder adapter — a purely visual Embedder on ONNX Runtime.

DINOv2 is self-supervised and maps an image to a 768-dim appearance embedding —
same bildaufbau/perspective/color/style land close together. Unlike SigLIP2/CLIP
it has NO text encoder: it satisfies the image-only `Embedder` protocol and NOT
`TextEmbedder`. That is the bauart limit P37 leans on — re-ranking only fires when
a query *image* exists (ADR-024).

Model directory layout (HF snapshot of onnx-community/dinov2-with-registers-base):
  <models_dir>/dinov2-with-registers-base/
      onnx/model.onnx          (fp32, self-contained — no external data)
      preprocessor_config.json
      config.json

The onnx export is a single vision graph; the global embedding is the CLS token.
`Dinov2Model` layernorms the last hidden state and takes token 0 as `pooler_output`
(register tokens do not shift the CLS position), so we prefer `pooler_output` and
fall back to `last_hidden_state[:, 0]`. The output is L2-normalized so cosine
similarity reduces to a dot product — the form the rerank (P37 Phase 3) needs.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import onnxruntime as ort

log = logging.getLogger(__name__)

_MANIFEST_ID = "dinov2-with-registers-base"


def _l2_normalize(vector: np.ndarray) -> np.ndarray:
    """Return the unit-norm version of a 1-D vector (guards the zero vector)."""
    flat = np.ascontiguousarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(flat))
    if norm == 0.0:
        return flat
    return flat / norm


def _pick_global_embedding(outputs: dict[str, np.ndarray]) -> np.ndarray:
    """Extract the 1-D global image embedding (CLS token) from the model outputs.

    Prefers the projected `pooler_output` (2-D, the layernormed CLS token). Falls
    back to token 0 of `last_hidden_state` (3-D) — the CLS token is at index 0
    whether or not register tokens follow. The name-agnostic tail covers exports
    whose output names differ from the transformers convention.
    """
    if "pooler_output" in outputs:
        return outputs["pooler_output"][0]
    if "last_hidden_state" in outputs:
        return outputs["last_hidden_state"][0, 0]
    for value in outputs.values():
        if value.ndim == 2:
            return value[0]
    for value in outputs.values():
        if value.ndim == 3:
            return value[0, 0]
    raise RuntimeError(f"DINOv2 model produced no usable embedding output (have {list(outputs)})")


class DINOv2Embedder:
    """Image-only Embedder backed by the onnx-community DINOv2-with-registers-base export.

    Satisfies the `Embedder` protocol (`dim` + `embed`) but deliberately NOT
    `TextEmbedder` — DINOv2 has no text path. The single ONNX vision session is
    owned by `session_manager` (lazy load / idle eviction).
    """

    dim: int = 768

    def __init__(self, model_dir: str) -> None:
        self._model_dir = Path(model_dir)
        self._vision_path = self._resolve("model.onnx")

    def _resolve(self, filename: str) -> str:
        """Find a model file under onnx/ (HF snapshot layout) or the dir root."""
        nested = self._model_dir / "onnx" / filename
        if nested.is_file():
            return str(nested)
        return str(self._model_dir / filename)

    # ------------------------------------------------------------------
    # Embedder protocol (image-only — no embed_text)
    # ------------------------------------------------------------------

    def embed(self, image: np.ndarray) -> np.ndarray:
        from photofant.inference.preprocessing import preprocess_for_dinov2
        from photofant.inference.session_manager import session_manager

        pixel_values = preprocess_for_dinov2(image)  # (1, 3, 224, 224) float32

        session = session_manager.acquire_session(self._vision_path)
        try:
            input_name = session.get_inputs()[0].name
            outputs = self._run(session, {input_name: pixel_values})
        finally:
            session_manager.release_session(self._vision_path)

        embedding = _pick_global_embedding(outputs)
        return _l2_normalize(embedding)

    @staticmethod
    def _run(session: ort.InferenceSession, feeds: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        from photofant.inference.session_manager import arena_shrink_run_options, run_with_oom_retry

        output_names = [output.name for output in session.get_outputs()]
        run_options = arena_shrink_run_options(session)
        results = run_with_oom_retry(
            lambda: session.run(output_names, feeds, run_options), description="DINOv2 inference"
        )
        return {name: value.astype(np.float32) for name, value in zip(output_names, results, strict=True)}
