"""Empfehlungs-Endpoint (P26 Phase 1) — Empfehlungen aus dem Cache + „Warum nicht?".

``GET /recommendations?asset_id=`` liefert die gecachten Empfehlungen eines Bildes. Fehlt
der Cache, wird der ``RecommendationJob`` geplant und eine leere Liste mit Status
``computing`` zurückgegeben — die Route rechnet **nie** synchron (Kontrakt: die UI
blockiert nie).

``GET /recommendations/{source}/{target}/why-not`` erklärt für ein konkretes Paar, welche
Signale fehlen bzw. unter der Schwelle liegen — live berechnet, nur auf Anfrage (P26-Risiko:
„Warum nicht?" nicht auf Vorrat).
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import AssetInstance, Recommendation
from photofant.db.session import get_session
from photofant.jobs.recommendation_job import enqueue_recommendation
from photofant.recommendation.context import build_context
from photofant.recommendation.scoring import (
    SIGNAL_CLIP,
    SIGNAL_SAME_FILM,
    SIGNAL_SAME_PERSON,
    SIGNAL_SAME_ROLE,
    Weights,
    pair_clip_similarity,
    score_pair,
)
from photofant.settings import load_settings

router = APIRouter(prefix="/recommendations")

DbSession = Annotated[Session, Depends(get_session)]

log = logging.getLogger(__name__)

STATUS_READY = "ready"
STATUS_COMPUTING = "computing"
STATUS_DISABLED = "disabled"

# Reihenfolge = Anzeigereihenfolge der Signale im „Warum nicht?"; die Gewichte kommen zur
# Laufzeit aus den settings.
_SIGNAL_ORDER = (SIGNAL_SAME_PERSON, SIGNAL_SAME_ROLE, SIGNAL_SAME_FILM, SIGNAL_CLIP)


class ReasonDto(BaseModel):
    signal: str
    detail: str
    weight: float


class RecommendationDto(BaseModel):
    asset_id: int
    thumbnail_url: str
    score: float
    reasons: list[ReasonDto]


class RecommendationsResponse(BaseModel):
    status: str  # ready | computing | disabled
    recommendations: list[RecommendationDto]


class WhyNotResponse(BaseModel):
    source_asset_id: int
    target_asset_id: int
    score: float
    threshold: float
    recommended: bool
    reasons: list[ReasonDto]  # anwesende Signale
    missing: list[ReasonDto]  # fehlende Signale (detail leer, weight = was es wert wäre)


@router.get("", response_model=RecommendationsResponse)
async def get_recommendations(asset_id: int, session: DbSession) -> RecommendationsResponse:
    settings = load_settings()
    if not settings["recommendations"]["enabled"]:
        return RecommendationsResponse(status=STATUS_DISABLED, recommendations=[])

    rows = _read_active_cache(session, asset_id)
    if not rows:
        await enqueue_recommendation(asset_id)
        return RecommendationsResponse(status=STATUS_COMPUTING, recommendations=[])

    recommendations = [
        RecommendationDto(
            asset_id=row.recommended_asset_id,
            thumbnail_url=f"/api/assets/{row.recommended_asset_id}/thumbnail",
            score=row.score,
            reasons=[ReasonDto(**reason) for reason in row.reasons],
        )
        for row in rows
    ]
    return RecommendationsResponse(status=STATUS_READY, recommendations=recommendations)


@router.get("/{source_asset_id}/{target_asset_id}/why-not", response_model=WhyNotResponse)
async def why_not(
    source_asset_id: int, target_asset_id: int, session: DbSession
) -> WhyNotResponse:
    settings = load_settings()
    rec_settings = settings["recommendations"]
    weights = Weights.from_settings(rec_settings["weights"])
    threshold = float(rec_settings["min_score"])

    source_context = build_context(session, source_asset_id)
    target_context = build_context(session, target_asset_id)
    clip_similarity = pair_clip_similarity(session, source_asset_id, target_asset_id)

    scored = score_pair(target_asset_id, source_context, target_context, clip_similarity, weights)
    present_signals = {reason.signal for reason in scored.reasons}
    weight_by_signal = {
        SIGNAL_SAME_PERSON: weights.same_person,
        SIGNAL_SAME_ROLE: weights.same_role,
        SIGNAL_SAME_FILM: weights.same_film,
        SIGNAL_CLIP: weights.clip_similarity,
    }
    missing = [
        ReasonDto(signal=signal, detail="", weight=weight_by_signal[signal])
        for signal in _SIGNAL_ORDER
        if signal not in present_signals
    ]

    return WhyNotResponse(
        source_asset_id=source_asset_id,
        target_asset_id=target_asset_id,
        score=scored.score,
        threshold=threshold,
        recommended=bool(scored.reasons) and scored.score >= threshold,
        reasons=[
            ReasonDto(signal=reason.signal, detail=reason.detail, weight=reason.weight)
            for reason in scored.reasons
        ],
        missing=missing,
    )


def _read_active_cache(session: Session, source_asset_id: int) -> list[Recommendation]:
    """Cache-Zeilen der Quelle, nach Score absteigend, ohne inzwischen gelöschte Ziele.

    Der Aktiv-Filter am Lesepunkt fängt Ziele ab, die nach dem Berechnen gelöscht wurden —
    der Cache selbst wird beim nächsten Job-Lauf wieder korrekt (jederzeit neu berechenbar).
    """
    active_targets = (
        select(AssetInstance.asset_id)
        .where(AssetInstance.deleted_at.is_(None))
        .scalar_subquery()
    )
    return list(
        session.execute(
            select(Recommendation)
            .where(Recommendation.source_asset_id == source_asset_id)
            .where(Recommendation.recommended_asset_id.in_(active_targets))
            .order_by(Recommendation.score.desc(), Recommendation.recommended_asset_id)
        )
        .scalars()
        .all()
    )
