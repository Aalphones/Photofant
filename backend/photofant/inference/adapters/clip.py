"""CLIP ViT-L/14 embedder adapter — implements the Embedder protocol on pure ONNX Runtime.

CLIP maps images and text into a shared 768-dim space, so a text query and an
image can be compared by cosine similarity. We run the onnx-community / Xenova
export on onnxruntime: separate `vision_model.onnx` (image → image_embeds) and
`text_model.onnx` (token ids → text_embeds), with the HuggingFace `tokenizers`
library as the only extra dependency for the text path.

Model directory layout (HF snapshot of Xenova/clip-vit-large-patch14):
  <models_dir>/clip-vit-l-14/
      onnx/vision_model.onnx
      onnx/text_model.onnx
      tokenizer.json

The image embedding is consumed by the import pipeline (Embedder.embed); the
text embedding backs the semantic-search endpoint (Embedder.embed_text). Both
outputs are L2-normalized so cosine similarity reduces to a dot product.
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

_MANIFEST_ID = "clip-vit-l-14"
_MAX_TEXT_TOKENS = 77  # CLIP's fixed context length


@lru_cache(maxsize=2)
def _load_tokenizer(tokenizer_path: str) -> Any:
    """Load the CLIP BPE tokenizer from tokenizer.json (cached per path)."""
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(tokenizer_path)
    tokenizer.enable_truncation(max_length=_MAX_TEXT_TOKENS)
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
    raise RuntimeError(f"CLIP model produced no 2-D embedding output (have {list(outputs)})")


class CLIPEmbedder:
    """Embedder backed by the onnx-community / Xenova CLIP ViT-L/14 export.

    The two ONNX sessions are owned by `session_manager` (lazy load / idle
    eviction); the tokenizer is cached globally per file.
    """

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
        from photofant.inference.preprocessing import preprocess_for_clip
        from photofant.inference.session_manager import session_manager

        pixel_values = preprocess_for_clip(image)  # (1, 3, 224, 224) float32

        session = session_manager.acquire_session(self._vision_path)
        try:
            input_name = session.get_inputs()[0].name
            outputs = self._run(session, {input_name: pixel_values})
        finally:
            session_manager.release_session(self._vision_path)

        embedding = _pick_embedding(outputs, "image_embeds")[0]
        return _l2_normalize(embedding)

    def warm_text(self) -> None:
        """Force-load the text encoder session without running inference.

        Used to prewarm the session in the background (e.g. while the user is
        still typing) so the actual `embed_text` call later hits an already
        loaded session instead of paying the multi-second cold-load cost.
        """
        from photofant.inference.session_manager import session_manager

        session_manager.acquire_session(self._text_path)
        session_manager.release_session(self._text_path)

    def embed_text(self, text: str) -> np.ndarray:
        from photofant.inference.session_manager import session_manager

        tokenizer = _load_tokenizer(self._tokenizer_path)
        encoding = tokenizer.encode(text)
        input_ids = np.array([encoding.ids], dtype=np.int64)
        attention_mask = np.array([encoding.attention_mask], dtype=np.int64)

        session = session_manager.acquire_session(self._text_path)
        try:
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
        output_names = [output.name for output in session.get_outputs()]
        results = session.run(output_names, feeds)
        return {name: value.astype(np.float32) for name, value in zip(output_names, results, strict=True)}


def resolve_clip_embedder() -> CLIPEmbedder | None:
    """Return a CLIPEmbedder if the model is enabled in the registry; None otherwise."""
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        entry = (
            session.query(ModelRegistry)
            .filter_by(manifest_id=_MANIFEST_ID, enabled=True)
            .first()
        )
        if entry is None or not entry.path:
            log.info("CLIP model not enabled or has no path — skipping")
            return None
        model_dir = entry.path

    return CLIPEmbedder(model_dir=model_dir)
