"""Face-Bereinigung — Score pro Face, wie sehr es zur zugewiesenen Person passt.

Kombiniert zwei unabhängige Signale (ADR-033):
  - Identität: Cosine-Distanz zum Personen-Embedding-Centroid (compute_person_centroid).
  - Qualität: schlechte Crop-Auflösung, niedriger Detection-Score, is_upscaled-Flag —
    das schlechteste der drei Signale zählt, keine Mittelung.

Stateless: keine Persistenz, jeder Aufruf rechnet frisch (Begründung: ADR-033).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.clustering.engine import compute_person_centroid
from photofant.db.models import Face

REASON_IDENTITY_MISMATCH = "identity_mismatch"
REASON_LOW_RESOLUTION = "low_resolution"
REASON_LOW_DETECTION_SCORE = "low_detection_score"
REASON_UPSCALED = "upscaled"


@dataclass
class FaceCleanupScore:
    face_id: int
    identity_distance: float | None
    cleanup_score: float
    reasons: list[str] = field(default_factory=list)


def _load_cleanup_settings() -> dict[str, float]:
    from photofant.settings import load_settings

    settings = load_settings()
    return {
        "min_faces": float(settings.get("face_cleanup_min_faces", 3)),
        "min_crop_side": float(settings.get("face_cleanup_min_crop_side", 100)),
        "low_score_threshold": float(settings.get("face_cleanup_low_score_threshold", 0.65)),
        "identity_weight": float(settings.get("face_cleanup_identity_weight", 0.6)),
        "quality_weight": float(settings.get("face_cleanup_quality_weight", 0.4)),
        "review_threshold": float(settings.get("face_review_threshold", 0.45)),
    }


def _clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def compute_person_cleanup_scores(session: Session, person_id: int) -> list[FaceCleanupScore]:
    """Score every face of a person by how likely it is a cleanup candidate.

    Returns one entry per face belonging to person_id, in no particular order —
    callers sort by cleanup_score themselves. Empty list if the person has no faces.
    """
    cfg = _load_cleanup_settings()

    rows = session.execute(
        select(Face.id, Face.embedding, Face.score, Face.resolution, Face.is_upscaled)
        .where(Face.person_id == person_id)
    ).all()

    if not rows:
        return []

    centroid: np.ndarray | None = None
    if len(rows) >= cfg["min_faces"]:
        centroid = compute_person_centroid(session, person_id)

    identity_norm = max(1.0 - cfg["review_threshold"], 1e-6)
    results: list[FaceCleanupScore] = []

    for face_id, embedding_bytes, score, resolution, is_upscaled in rows:
        reasons: list[str] = []
        identity_distance: float | None = None
        identity_penalty = 0.0

        if centroid is not None and embedding_bytes is not None:
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            similarity = float(np.dot(embedding, centroid))
            identity_distance = 1.0 - similarity
            identity_penalty = _clamp01(identity_distance / identity_norm)
            if identity_penalty >= 0.5:
                reasons.append(REASON_IDENTITY_MISMATCH)

        res_penalty = 0.0
        if resolution is not None and resolution > 0:
            crop_side = resolution ** 0.5
            if crop_side < cfg["min_crop_side"]:
                reasons.append(REASON_LOW_RESOLUTION)
                res_penalty = _clamp01((cfg["min_crop_side"] - crop_side) / cfg["min_crop_side"])

        score_penalty = 0.0
        if score is not None and score < cfg["low_score_threshold"]:
            reasons.append(REASON_LOW_DETECTION_SCORE)
            score_penalty = _clamp01(
                (cfg["low_score_threshold"] - score) / cfg["low_score_threshold"]
            )

        upscale_penalty = 0.0
        if is_upscaled:
            reasons.append(REASON_UPSCALED)
            upscale_penalty = 1.0

        quality_penalty = max(res_penalty, score_penalty, upscale_penalty)
        cleanup_score = _clamp01(
            cfg["identity_weight"] * identity_penalty + cfg["quality_weight"] * quality_penalty
        )

        results.append(FaceCleanupScore(
            face_id=int(face_id),
            identity_distance=identity_distance,
            cleanup_score=cleanup_score,
            reasons=reasons,
        ))

    return results
