"""WD14 SwinV2 v3 tagger adapter — implements the Tagger protocol.

Model directory layout (after download):
  <models_dir>/wd-swinv2-v3/
      model.onnx          — SwinV2 ONNX
      selected_tags.csv   — tag_id,name,category (category 9 = rating, filtered)
"""
from __future__ import annotations

import csv
import logging
from functools import lru_cache
from pathlib import Path

import numpy as np

from photofant.inference.interfaces import TagScore

log = logging.getLogger(__name__)

_MANIFEST_ID = "wd-swinv2-v3"
_DEFAULT_THRESHOLD: float = 0.35
_RATING_CATEGORY: int = 9


@lru_cache(maxsize=4)
def _load_labels(csv_path: str) -> list[tuple[str, bool]]:
    """Parse selected_tags.csv → (name, is_rating) per row, in model-output order.

    Cached by path so a second call hits memory, not disk.
    """
    labels: list[tuple[str, bool]] = []
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            is_rating = int(row["category"]) == _RATING_CATEGORY
            labels.append((row["name"], is_rating))
    log.debug("Loaded %d WD14 labels from %s", len(labels), csv_path)
    return labels


class WD14Tagger:
    """Tagger backed by a WD14 SwinV2 v3 ONNX model.

    ONNX session is owned by session_manager (lazy load / idle eviction).
    CSV labels are cached globally per csv_path.
    """

    def __init__(self, model_dir: str, threshold: float = _DEFAULT_THRESHOLD) -> None:
        self._model_dir = Path(model_dir)
        self._model_path = str(self._model_dir / "model.onnx")
        self._csv_path = str(self._model_dir / "selected_tags.csv")
        self._threshold = threshold

    def tag(self, image: np.ndarray) -> list[TagScore]:
        from photofant.inference.preprocessing import preprocess_for_wd14
        from photofant.inference.session_manager import session_manager
        from photofant.settings import load_settings

        labels = _load_labels(self._csv_path)
        input_array = preprocess_for_wd14(image)

        pool_size = load_settings()["tagging_workers"]
        session = session_manager.acquire_exclusive_session(self._model_path, pool_size)
        try:
            input_name = session.get_inputs()[0].name
            raw_outputs = session.run(None, {input_name: input_array})
        finally:
            session_manager.release_exclusive_session(self._model_path, session)

        logits: np.ndarray = raw_outputs[0][0].astype(np.float32)
        scores = 1.0 / (1.0 + np.exp(-logits))  # sigmoid

        results: list[TagScore] = []
        for index, (name, is_rating) in enumerate(labels):
            if is_rating:
                continue
            score = float(scores[index])
            if score >= self._threshold:
                results.append(TagScore(name=name, score=score))

        results.sort(key=lambda tag_score: tag_score.score, reverse=True)
        log.debug("WD14: %d tags above threshold %.2f", len(results), self._threshold)
        return results


def resolve_wd14_tagger(threshold: float = _DEFAULT_THRESHOLD) -> WD14Tagger | None:
    """Return a WD14Tagger if the model is enabled in the registry; None otherwise."""
    from photofant.db.models import ModelRegistry
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        entry = (
            session.query(ModelRegistry)
            .filter_by(manifest_id=_MANIFEST_ID, enabled=True)
            .first()
        )
        if entry is None or not entry.path:
            log.info("WD14 model not enabled or has no path — skipping")
            return None
        model_dir = entry.path

    return WD14Tagger(model_dir=model_dir, threshold=threshold)
