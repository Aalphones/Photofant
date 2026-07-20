"""RecommendationJob-Cache-Schreibpfad (P26 Phase 1) — ``store_recommendations`` ersetzt
die Cache-Zeilen der Quelle idempotent (kein Merge, der Cache ist neu berechenbar)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from photofant.db.models import Asset, Recommendation
from photofant.jobs.recommendation_job import invalidate_recommendations, store_recommendations
from photofant.recommendation.scoring import Reason, ScoredRecommendation


def _add_asset(session: Session, asset_id: int) -> None:
    session.add(Asset(id=asset_id, content_hash=f"hash-{asset_id}"))


def test_store_recommendations_persists_rows_with_reasons(db_session: Session) -> None:
    _add_asset(db_session, 100)
    _add_asset(db_session, 101)

    store_recommendations(
        db_session,
        100,
        [
            ScoredRecommendation(
                asset_id=101,
                score=0.65,
                reasons=[
                    Reason("same_person", "Robert Downey Jr.", 0.4),
                    Reason("same_role", "Tony Stark", 0.25),
                ],
            )
        ],
    )
    db_session.commit()

    rows = db_session.query(Recommendation).filter_by(source_asset_id=100).all()
    assert len(rows) == 1
    assert rows[0].recommended_asset_id == 101
    assert rows[0].score == 0.65
    assert rows[0].reasons == [
        {"signal": "same_person", "detail": "Robert Downey Jr.", "weight": 0.4},
        {"signal": "same_role", "detail": "Tony Stark", "weight": 0.25},
    ]
    assert rows[0].computed_at is not None


def test_store_recommendations_replaces_previous_rows(db_session: Session) -> None:
    _add_asset(db_session, 100)
    _add_asset(db_session, 101)
    _add_asset(db_session, 102)

    store_recommendations(
        db_session, 100, [ScoredRecommendation(asset_id=101, score=0.5, reasons=[])]
    )
    db_session.commit()

    store_recommendations(
        db_session, 100, [ScoredRecommendation(asset_id=102, score=0.7, reasons=[])]
    )
    db_session.commit()

    rows = db_session.query(Recommendation).filter_by(source_asset_id=100).all()
    assert [row.recommended_asset_id for row in rows] == [102]


def test_invalidate_recommendations_deletes_rows_where_asset_is_source(db_session: Session) -> None:
    _add_asset(db_session, 100)
    _add_asset(db_session, 101)
    store_recommendations(
        db_session, 100, [ScoredRecommendation(asset_id=101, score=0.5, reasons=[])]
    )
    db_session.commit()

    invalidate_recommendations(db_session, [100])
    db_session.commit()

    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []


def test_invalidate_recommendations_deletes_rows_where_asset_is_target(db_session: Session) -> None:
    _add_asset(db_session, 100)
    _add_asset(db_session, 101)
    store_recommendations(
        db_session, 100, [ScoredRecommendation(asset_id=101, score=0.5, reasons=[])]
    )
    db_session.commit()

    # Nur die Ziel-Seite (101) wird invalidiert, nicht die Quelle (100) — das ist der
    # Kern-Fix: bisher wurde nur source_asset_id je gelöscht.
    invalidate_recommendations(db_session, [101])
    db_session.commit()

    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []


def test_invalidate_recommendations_empty_list_is_noop(db_session: Session) -> None:
    _add_asset(db_session, 100)
    _add_asset(db_session, 101)
    store_recommendations(
        db_session, 100, [ScoredRecommendation(asset_id=101, score=0.5, reasons=[])]
    )
    db_session.commit()

    invalidate_recommendations(db_session, [])
    db_session.commit()

    assert len(db_session.query(Recommendation).filter_by(source_asset_id=100).all()) == 1
