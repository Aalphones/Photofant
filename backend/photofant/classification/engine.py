"""Classification engine — CLIP + WD14 fusion (P18 Phase 2).

Contract: docs/planning/2026-06-30_p18-bildklassifizierung/README.md.

Reads already-computed signals (the stored semantic embedding, `asset_tag.score`) —
never loads the image and never runs a vision model. The retro-run over an
existing library is therefore cheap: no model inference, just DB reads +
fusion math.

Fusion per (category, label):
    clip_p  = softmax over cosine(image_embedding, mean(label prompt embeddings))
    wd14_p  = max(stored tag score) over label.wd14_tags, or None if none stored
    fused   = weighted blend of whichever signal(s) are available
Category mode decides selection: single -> argmax >= min_confidence (category
override or the global default), multi -> every label >= multi_min_confidence.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from photofant.classification.scoring import score_label_wd14, score_labels_clip
from photofant.db import embeddings
from photofant.db.models import Asset, AssetTag, ClassificationCategory, ClassificationLabel, Tag
from photofant.inference.image_embedder import resolve_image_embedder
from photofant.settings import load_settings

log = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    category_id: int
    label_id: int
    confidence: float
    source: str  # 'clip' | 'wd14' | 'fused'


def _stored_tag_scores(session: Session, asset_id: int) -> dict[str, float]:
    """Tag name -> stored WD14 score for one asset (manually-removed tags excluded)."""
    rows = (
        session.query(Tag.name, AssetTag.score)
        .join(AssetTag, AssetTag.tag_id == Tag.id)
        .filter(AssetTag.asset_id == asset_id, AssetTag.manually_removed.is_(False))
        .all()
    )
    return {name: score for name, score in rows if score is not None}


def _label_clip_prompts(label: ClassificationLabel, template: str) -> list[str]:
    if label.clip_prompts:
        return label.clip_prompts
    return [template.format(label=label.name)]


def _fuse(
    clip_probability: float | None,
    wd14_probability: float | None,
    clip_weight: float,
    wd14_weight: float,
) -> tuple[float, str]:
    """Weighted blend of whichever signal(s) are present; source tags which one(s) won."""
    if clip_probability is not None and wd14_probability is not None:
        total_weight = clip_weight + wd14_weight
        if total_weight <= 0:
            return 0.0, "fused"
        fused = (clip_probability * clip_weight + wd14_probability * wd14_weight) / total_weight
        return fused, "fused"
    if clip_probability is not None:
        return clip_probability, "clip"
    if wd14_probability is not None:
        return wd14_probability, "wd14"
    return 0.0, "fused"  # neither signal — never clears a threshold, effectively "entfällt"


def classify_asset(session: Session, asset_id: int) -> list[ClassificationResult]:
    """Fuse CLIP + WD14 signals into classifications for every enabled category.

    No commit — the caller owns the transaction.
    """
    asset = session.get(Asset, asset_id)
    if asset is None:
        log.warning("classify_asset: asset %d not found", asset_id)
        return []

    settings = load_settings()["classification"]
    clip_weight = settings["clip_weight"]
    wd14_weight = settings["wd14_weight"]
    default_min_confidence = settings["min_confidence"]
    multi_min_confidence = settings["multi_min_confidence"]
    prompt_template = settings["clip_prompt_template"]

    image_embedding: np.ndarray | None = None
    if resolve_image_embedder() is not None:
        image_embedding = embeddings.get_semantic(session, asset_id)

    tag_scores = _stored_tag_scores(session, asset_id)

    categories = (
        session.query(ClassificationCategory)
        .filter(ClassificationCategory.enabled.is_(True))
        .all()
    )

    results: list[ClassificationResult] = []
    for category in categories:
        labels = (
            session.query(ClassificationLabel)
            .filter(ClassificationLabel.category_id == category.id)
            .order_by(ClassificationLabel.position)
            .all()
        )
        if not labels:
            continue

        clip_scores: list[float | None] = [None] * len(labels)
        if image_embedding is not None:
            prompts_per_label = [_label_clip_prompts(label, prompt_template) for label in labels]
            clip_scores = list(score_labels_clip(image_embedding, prompts_per_label))

        wd14_scores = [score_label_wd14(label.wd14_tags, tag_scores) for label in labels]

        fused = [
            _fuse(clip_scores[index], wd14_scores[index], clip_weight, wd14_weight)
            for index in range(len(labels))
        ]

        min_confidence = (
            category.min_confidence if category.min_confidence is not None else default_min_confidence
        )

        if category.mode == "single":
            best_index = max(range(len(labels)), key=lambda index: fused[index][0])
            best_confidence, best_source = fused[best_index]
            if best_confidence >= min_confidence:
                results.append(ClassificationResult(
                    category_id=category.id,
                    label_id=labels[best_index].id,
                    confidence=best_confidence,
                    source=best_source,
                ))
        else:  # multi
            for index, label in enumerate(labels):
                confidence, source = fused[index]
                if confidence >= multi_min_confidence:
                    results.append(ClassificationResult(
                        category_id=category.id,
                        label_id=label.id,
                        confidence=confidence,
                        source=source,
                    ))

    return results
