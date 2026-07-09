"""Scoring-Kern der Empfehlungen (P26 Phase 1) — der heikle Teil.

Der Score kombiniert **zwei** unabhängige Quellen (Kontrakt-AK: nicht nur CLIP):

- **Bild-Ähnlichkeit** — die CLIP/SigLIP2-Kosinus-Nähe aus dem bestehenden Vektorindex
  (``db/vector_index.py``), 0..1.
- **Wissensgraph** — geteilte Person / Rolle / Film aus dem Kontext (``context.py``),
  je 0 oder 1.

    score = w_person·[gleiche Person] + w_role·[gleiche Rolle]
          + w_film·[gleicher Film]   + w_clip·clip_similarity

Die Gewichte kommen aus den settings (kalibrierbar, Default summiert zu 1.0 → Score in
[0, 1], damit ``min_score`` direkt interpretierbar ist). Jede beitragende Größe erzeugt
ein Reason-Chain-Glied mit konkretem Signalwert — so ist eine Fehlgewichtung sichtbar
statt versteckt (P26-Risiko).

Kandidaten kommen aus beiden Quellen zusammen: CLIP-Nachbarn (mit Ähnlichkeitswert) und
graph-verbundene Assets (ohne CLIP-Wert). Ein Kandidat, der in beiden auftaucht, trägt
beide Signalarten — genau der belegbare „CLIP **und** Graph"-Fall der AK.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db import vector_index
from photofant.db.models import Asset, AssetInstance
from photofant.recommendation.context import (
    AssetGraphContext,
    build_context,
    build_contexts,
    gather_graph_candidates,
)
from photofant.settings import AppSettings, RecommendationWeights

SIGNAL_CLIP = "clip"
SIGNAL_SAME_PERSON = "same_person"
SIGNAL_SAME_ROLE = "same_role"
SIGNAL_SAME_FILM = "same_film"

# CLIP-Kandidaten-Pool: wie in `api/search.py` ist die Über-Anforderung ein Modul-Konstant,
# kein settings-Wert (kein tunbarer Fachparameter, nur Puffer gegen den min_score-Filter).
_CANDIDATE_FACTOR = 8
_CANDIDATE_FLOOR = 40


@dataclass
class Reason:
    """Ein Glied der Begründungskette: welches Signal, sein konkreter Wert, sein Gewicht."""

    signal: str
    detail: str
    weight: float

    def to_dict(self) -> dict[str, object]:
        return {"signal": self.signal, "detail": self.detail, "weight": self.weight}


@dataclass
class ScoredRecommendation:
    asset_id: int
    score: float
    reasons: list[Reason]


@dataclass
class Weights:
    same_person: float
    same_role: float
    same_film: float
    clip_similarity: float

    @classmethod
    def from_settings(cls, weights: RecommendationWeights) -> Weights:
        return cls(
            same_person=float(weights["same_person"]),
            same_role=float(weights["same_role"]),
            same_film=float(weights["same_film"]),
            clip_similarity=float(weights["clip_similarity"]),
        )


def score_pair(
    asset_id: int,
    source_context: AssetGraphContext,
    candidate_context: AssetGraphContext,
    clip_similarity: float | None,
    weights: Weights,
) -> ScoredRecommendation:
    """Bewertet ein Kandidaten-Asset gegen die Quelle. Nur **anwesende** Signale erzeugen
    ein Reason-Glied; ``clip_similarity=None`` (Graph-Kandidat ohne CLIP-Wert) trägt nichts
    zum Bild-Anteil bei."""
    reasons: list[Reason] = []
    score = 0.0

    person_name = _shared_person(source_context.persons, candidate_context.persons)
    if person_name is not None:
        reasons.append(Reason(SIGNAL_SAME_PERSON, person_name, weights.same_person))
        score += weights.same_person

    role_title = _shared_title(source_context.roles, candidate_context.roles)
    if role_title is not None:
        reasons.append(Reason(SIGNAL_SAME_ROLE, role_title, weights.same_role))
        score += weights.same_role

    film_title = _shared_title(source_context.films, candidate_context.films)
    if film_title is not None:
        reasons.append(Reason(SIGNAL_SAME_FILM, film_title, weights.same_film))
        score += weights.same_film

    if clip_similarity is not None and clip_similarity > 0.0:
        reasons.append(Reason(SIGNAL_CLIP, f"{clip_similarity:.2f}", weights.clip_similarity))
        score += weights.clip_similarity * clip_similarity

    return ScoredRecommendation(asset_id=asset_id, score=score, reasons=reasons)


def compute_recommendations(
    session: Session, source_asset_id: int, settings: AppSettings
) -> list[ScoredRecommendation]:
    """Berechnet die Top-Empfehlungen für ein Quell-Asset (leer, wenn abgeschaltet).

    Rein lesend + rechnend — das Schreiben in den Cache macht der Job (``recommendation_job``).
    """
    rec_settings = settings["recommendations"]
    if not rec_settings["enabled"]:
        return []

    weights = Weights.from_settings(rec_settings["weights"])
    min_score = float(rec_settings["min_score"])
    max_results = int(rec_settings["max_results"])

    source_context = build_context(session, source_asset_id)
    candidate_similarities = _gather_candidates(session, source_asset_id, source_context, max_results)
    if not candidate_similarities:
        return []

    active = _active_asset_ids(session, list(candidate_similarities))
    candidate_ids = [asset_id for asset_id in candidate_similarities if asset_id in active]
    candidate_contexts = build_contexts(session, candidate_ids)

    scored: list[ScoredRecommendation] = []
    for asset_id in candidate_ids:
        recommendation = score_pair(
            asset_id,
            source_context,
            candidate_contexts.get(asset_id, AssetGraphContext()),
            candidate_similarities[asset_id],
            weights,
        )
        if recommendation.reasons and recommendation.score >= min_score:
            scored.append(recommendation)

    scored.sort(key=lambda recommendation: (-recommendation.score, recommendation.asset_id))
    return scored[:max_results]


def cosine_similarity(first: np.ndarray, second: np.ndarray) -> float:
    """Kosinus-Ähnlichkeit zweier Embeddings (0, wenn ein Vektor Länge 0 hat)."""
    first_norm = float(np.linalg.norm(first))
    second_norm = float(np.linalg.norm(second))
    if first_norm == 0.0 or second_norm == 0.0:
        return 0.0
    return float(np.dot(first, second) / (first_norm * second_norm))


def pair_clip_similarity(session: Session, source_asset_id: int, target_asset_id: int) -> float | None:
    """CLIP-Ähnlichkeit zwischen zwei konkreten Assets — für ``why-not`` (Einzelpaar,
    kein Vektorindex-Scan). ``None``, wenn einem Asset das Embedding fehlt."""
    source_embedding = _load_embedding(session, source_asset_id)
    target_embedding = _load_embedding(session, target_asset_id)
    if source_embedding is None or target_embedding is None:
        return None
    return cosine_similarity(source_embedding, target_embedding)


# ----------------------------------------------------------------------------
# Interna
# ----------------------------------------------------------------------------


def _shared_person(source: dict[int, str], candidate: dict[int, str]) -> str | None:
    shared = set(source) & set(candidate)
    if not shared:
        return None
    first = min(shared)
    return source.get(first) or candidate.get(first) or f"Person {first}"


def _shared_title(source: dict[str, str], candidate: dict[str, str]) -> str | None:
    shared = set(source) & set(candidate)
    if not shared:
        return None
    first = min(shared)
    return source.get(first) or candidate.get(first) or first


def _gather_candidates(
    session: Session, source_asset_id: int, source_context: AssetGraphContext, max_results: int
) -> dict[int, float | None]:
    """Kandidaten aus beiden Quellen: CLIP-Nachbarn (mit Ähnlichkeit) + Graph (ohne). Ein
    Kandidat aus beiden behält seinen CLIP-Wert. Die Quelle selbst fällt raus."""
    similarities: dict[int, float | None] = {}
    for asset_id, similarity in _clip_candidates(session, source_asset_id, max_results):
        similarities[asset_id] = similarity
    for asset_id in gather_graph_candidates(session, source_context):
        similarities.setdefault(asset_id, None)
    similarities.pop(source_asset_id, None)
    return similarities


def _clip_candidates(
    session: Session, source_asset_id: int, max_results: int
) -> list[tuple[int, float]]:
    embedding = _load_embedding(session, source_asset_id)
    if embedding is None:
        return []
    pool_size = max(max_results * _CANDIDATE_FACTOR, max_results + _CANDIDATE_FLOOR)
    return [
        (asset_id, similarity)
        for asset_id, similarity in vector_index.search(session, embedding, pool_size)
        if asset_id != source_asset_id
    ]


def _load_embedding(session: Session, asset_id: int) -> np.ndarray | None:
    asset = session.get(Asset, asset_id)
    if asset is None or asset.clip_embedding is None:
        return None
    return np.frombuffer(asset.clip_embedding, dtype=np.float32)


def _active_asset_ids(session: Session, asset_ids: list[int]) -> set[int]:
    """Assets mit mindestens einer nicht-gelöschten Instanz (gleiche Aktiv-Definition wie
    ``api/search.py``)."""
    if not asset_ids:
        return set()
    rows = session.execute(
        select(AssetInstance.asset_id)
        .where(AssetInstance.asset_id.in_(asset_ids))
        .where(AssetInstance.deleted_at.is_(None))
    ).all()
    return {asset_id for (asset_id,) in rows}
