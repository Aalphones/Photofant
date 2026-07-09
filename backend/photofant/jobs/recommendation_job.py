"""RecommendationJob (P26 Phase 1) — Empfehlungen berechnen und cachen.

Kombiniert CLIP-Bildähnlichkeit mit dem Wissensgraph zu einem gewichteten Score samt
Begründungskette (``recommendation/scoring.py``) und legt das Ergebnis in
``recommendation_cache`` ab. Läuft als Job statt synchron im REST-Handler, weil die
API-Route nie rechnen darf (Kontrakt: die UI blockiert nie — Empfehlungen kommen aus
dem Cache, ein Cache-Fehltreffer plant diesen Job).

Idempotent: der Job **ersetzt** die Cache-Zeilen der Quelle vollständig. Damit bedient
derselbe Job „auf Abruf berechnen" (Cache-Fehltreffer) und „nach einer Graph-Änderung
neu berechnen" — ein separater ``RecommendationUpdateJob`` (README-Kontrakt) wäre
verhaltensgleich und damit nur Rauschen. Auto-Trigger bei Graph-Änderungen sind spätere
Integration (nicht Phase-1-Scope).

Reine Sackgasse wie ``KnowledgeLookupJob``/``KnowledgePatchJob``: löst keine Folge-Jobs aus.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from photofant.db.models import Recommendation
from photofant.db.session import SessionLocal
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.recommendation.scoring import ScoredRecommendation, compute_recommendations
from photofant.settings import load_settings

log = logging.getLogger(__name__)


def store_recommendations(
    session: Session, source_asset_id: int, recommendations: list[ScoredRecommendation]
) -> None:
    """Ersetzt die Cache-Zeilen der Quelle vollständig (kein Merge — der Cache ist neu
    berechenbar). Kein Commit — der Aufrufer besitzt die Transaktion."""
    session.query(Recommendation).filter_by(source_asset_id=source_asset_id).delete()
    computed_at = datetime.utcnow()
    for recommendation in recommendations:
        session.add(
            Recommendation(
                source_asset_id=source_asset_id,
                recommended_asset_id=recommendation.asset_id,
                score=recommendation.score,
                reasons=[reason.to_dict() for reason in recommendation.reasons],
                computed_at=computed_at,
            )
        )


def _run_recommendation(source_asset_id: int) -> None:
    settings = load_settings()
    with SessionLocal() as session:
        recommendations = compute_recommendations(session, source_asset_id, settings)
        store_recommendations(session, source_asset_id, recommendations)
        session.commit()
        log.info(
            "recommendation: Bild %d → %d Empfehlung(en) berechnet",
            source_asset_id,
            len(recommendations),
        )


async def run_recommendation_job(status: JobStatus, source_asset_id: int) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_recommendation, source_asset_id)


async def enqueue_recommendation(source_asset_id: int) -> JobStatus:
    async def _factory(status: JobStatus) -> None:
        await run_recommendation_job(status, source_asset_id)

    return await job_queue.enqueue(
        kind=JobKind.RECOMMENDATION,
        label=f"Empfehlungen: Bild {source_asset_id}",
        coro_factory=_factory,
    )
