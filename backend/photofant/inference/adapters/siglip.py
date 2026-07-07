"""SigLIP2 large-patch16-384 embedder adapter — implements the Embedder protocol on pure ONNX Runtime.

SigLIP2 maps images and text into a shared 1024-dim space, so a text query and
an image can be compared by cosine similarity. We run the onnx-community export
on onnxruntime: separate `vision_model.onnx` (image → image_embeds) and
`text_model.onnx` (token ids → text_embeds), with the HuggingFace `tokenizers`
library as the only extra dependency for the text path.

Model directory layout (HF snapshot of onnx-community/siglip2-large-patch16-384-ONNX):
  <models_dir>/siglip2-large-patch16-384/
      onnx/vision_model.onnx
      onnx/text_model.onnx
      tokenizer.json

SigLIP2's contract differs from CLIP in two ways that matter here:
  * image preprocessing squashes to 384² (no center-crop) and normalizes with
    mean/std 0.5 — see `preprocess_for_siglip`;
  * text uses a fixed 64-token padded length (Gemma multilingual tokenizer),
    not CLIP's 77-token truncation.
Both outputs are L2-normalized so cosine similarity reduces to a dot product.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import onnxruntime as ort

log = logging.getLogger(__name__)

_MANIFEST_ID = "siglip2-large-patch16-384"
_MAX_TEXT_TOKENS = 64  # SigLIP2's fixed, padded context length


@lru_cache(maxsize=2)
def _load_tokenizer(tokenizer_path: str) -> Any:
    """Load the SigLIP2 tokenizer from tokenizer.json (cached per path).

    SigLIP2 feeds the text encoder a *fixed-length* sequence: every query is
    truncated AND padded to 64 tokens. The pad token comes from the tokenizer's
    own config; verify `model_max_length` == 64 against tokenizer_config.json
    after download.
    """
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(tokenizer_path)
    tokenizer.enable_truncation(max_length=_MAX_TEXT_TOKENS)
    tokenizer.enable_padding(length=_MAX_TEXT_TOKENS)
    return tokenizer


def _l2_normalize(vector: np.ndarray) -> np.ndarray:
    """Return the unit-norm version of a 1-D vector (guards the zero vector)."""
    flat = np.ascontiguousarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(flat))
    if norm == 0.0:
        return flat
    return flat / norm


def _pick_embedding(outputs: dict[str, np.ndarray], preferred: str) -> np.ndarray:
    """Pick the projected-embedding output by name, else the first 2-D output."""
    if preferred in outputs:
        return outputs[preferred]
    for value in outputs.values():
        if value.ndim == 2:
            return value
    raise RuntimeError(f"SigLIP model produced no 2-D embedding output (have {list(outputs)})")


class SigLIPEmbedder:
    """Embedder backed by the onnx-community SigLIP2 large-patch16-384 export.

    The two ONNX sessions are owned by `session_manager` (lazy load / idle
    eviction); the tokenizer is cached globally per file. Mirrors `CLIPEmbedder`
    but carries SigLIP2's preprocessing/text contract and 1024-dim output.
    """

    dim: int = 1024

    def __init__(self, model_dir: str) -> None:
        self._model_dir = Path(model_dir)
        self._vision_path = self._resolve("vision_model.onnx")
        self._text_path = self._resolve("text_model.onnx")
        self._tokenizer_path = str(self._model_dir / "tokenizer.json")

    def _resolve(self, filename: str) -> str:
        """Find a model file under onnx/ (HF snapshot layout) or the dir root."""
        nested = self._model_dir / "onnx" / filename
        if nested.is_file():
            return str(nested)
        return str(self._model_dir / filename)

    # ------------------------------------------------------------------
    # Embedder protocol
    # ------------------------------------------------------------------

    def embed(self, image: np.ndarray) -> np.ndarray:
        from photofant.inference.preprocessing import preprocess_for_siglip
        from photofant.inference.session_manager import session_manager

        pixel_values = preprocess_for_siglip(image)  # (1, 3, 384, 384) float32

        session = session_manager.acquire_session(self._vision_path)
        try:
            input_name = session.get_inputs()[0].name
            outputs = self._run(session, {input_name: pixel_values})
        finally:
            session_manager.release_session(self._vision_path)

        embedding = _pick_embedding(outputs, "image_embeds")[0]
        return _l2_normalize(embedding)

    def embed_text(self, text: str) -> np.ndarray:
        from photofant.inference.session_manager import session_manager

        tokenizer = _load_tokenizer(self._tokenizer_path)
        encoding = tokenizer.encode(text)
        input_ids = np.array([encoding.ids], dtype=np.int64)
        attention_mask = np.array([encoding.attention_mask], dtype=np.int64)

        session = session_manager.acquire_session(self._text_path)
        try:
            # SigLIP2's text model is typically fed padded ids with no mask;
            # send attention_mask only if this export actually declares it.
            declared = {model_input.name for model_input in session.get_inputs()}
            feeds: dict[str, np.ndarray] = {"input_ids": input_ids}
            if "attention_mask" in declared:
                feeds["attention_mask"] = attention_mask
            outputs = self._run(session, feeds)
        finally:
            session_manager.release_session(self._text_path)

        embedding = _pick_embedding(outputs, "text_embeds")[0]
        return _l2_normalize(embedding)

    @staticmethod
    def _run(session: ort.InferenceSession, feeds: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        from photofant.inference.session_manager import arena_shrink_run_options, run_with_oom_retry

        output_names = [output.name for output in session.get_outputs()]
        run_options = arena_shrink_run_options(session)
        results = run_with_oom_retry(
            lambda: session.run(output_names, feeds, run_options), description="SigLIP inference"
        )
        return {name: value.astype(np.float32) for name, value in zip(output_names, results, strict=True)}
