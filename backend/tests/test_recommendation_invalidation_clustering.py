"""Recommendation-Cache-Invalidierung bei automatischer Personen-Zuordnung (Phase 4 des
Plans ``2026-07-20_recommendation-cache-invalidation``).

Vor diesem Plan hatte der Clustering-Pfad keinen einzigen Invalidierungs-Hook. Anders als
Phase 2/3 gibt es hier kein bestehendes Muster zum 1:1-Abschauen, deshalb decken die Tests
beide Zuordnungs-Zweige in ``run_initial_clustering`` (Pre-Match und HDBSCAN) sowie den
Auto-Zweig in ``run_incremental_match`` separat ab — ``match_face_incremental`` und
``_run_hdbscan`` werden gemockt statt echte Embeddings/Clustering zu berechnen.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy.orm import Session

from photofant.clustering import engine
from photofant.clustering.engine import MatchResult, run_initial_clustering
from photofant.db.models import Asset, Face, Person, Recommendation
from photofant.jobs import clustering_job


def _add_asset(session: Session, asset_id: int) -> None:
    session.add(Asset(id=asset_id, content_hash=f"hash-{asset_id}"))


def _seed_recommendation(session: Session, source_id: int, target_id: int) -> None:
    session.add(
        Recommendation(
            source_asset_id=source_id,
            recommended_asset_id=target_id,
            score=0.5,
            reasons=[],
            computed_at=datetime.utcnow(),
        )
    )
    session.commit()


def test_run_initial_clustering_pre_match_invalidates_recommendations(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    _seed_recommendation(db_session, source_id=100, target_id=200)

    target_person = Person(name="Target", is_unknown=False)
    db_session.add(target_person)
    db_session.flush()

    face = Face(
        asset_id=100,
        person_id=1,
        crop_path="unused.jpg",
        embedding=np.zeros(512, dtype=np.float32).tobytes(),
    )
    db_session.add(face)
    db_session.commit()

    monkeypatch.setattr(
        engine,
        "match_face_incremental",
        lambda session, face_id: MatchResult(person_id=target_person.id, score=0.9, band="auto"),
    )
    # Ein einzelnes Embedding lässt echtes sklearn-HDBSCAN mit ValueError("n_samples=1 ...")
    # abbrechen statt "leer durchzulaufen" (Annahme in der Phasen-Datei war ungenau) — der
    # Pre-Match-Zweig ist bereits gelaufen, wenn HDBSCAN startet, also stubben statt fixen.
    monkeypatch.setattr(
        engine,
        "_run_hdbscan",
        lambda embeddings, min_cluster_size, epsilon: np.full(len(embeddings), -1),
    )

    run_initial_clustering(db_session)

    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []


def test_run_initial_clustering_hdbscan_invalidates_recommendations(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    _seed_recommendation(db_session, source_id=100, target_id=200)

    face_a = Face(
        asset_id=100,
        person_id=1,
        crop_path="unused-a.jpg",
        embedding=np.zeros(512, dtype=np.float32).tobytes(),
    )
    face_b = Face(
        asset_id=200,
        person_id=1,
        crop_path="unused-b.jpg",
        embedding=np.zeros(512, dtype=np.float32).tobytes(),
    )
    db_session.add_all([face_a, face_b])
    db_session.commit()

    # Pre-Match-Zweig soll für keins der beiden Faces greifen, damit sie für HDBSCAN übrig bleiben.
    monkeypatch.setattr(
        engine,
        "match_face_incremental",
        lambda session, face_id: MatchResult(person_id=None, score=0.0, band="unknown"),
    )
    # Beide Faces landen deterministisch in Cluster 0, statt echtes HDBSCAN laufen zu lassen.
    monkeypatch.setattr(
        engine,
        "_run_hdbscan",
        lambda embeddings, min_cluster_size, epsilon: np.array([0, 0]),
    )

    run_initial_clustering(db_session)

    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []


def test_run_incremental_match_auto_invalidates_recommendations(
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    _seed_recommendation(db_session, source_id=100, target_id=200)

    target_person = Person(name="Target", is_unknown=False)
    db_session.add(target_person)
    db_session.flush()

    face = Face(asset_id=100, person_id=1, crop_path="unused.jpg")
    db_session.add(face)
    db_session.commit()

    monkeypatch.setattr(clustering_job, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(
        engine,
        "match_face_incremental",
        lambda session, face_id: MatchResult(person_id=target_person.id, score=0.9, band="auto"),
    )
    monkeypatch.setattr("photofant.config.get_data_root", lambda: tmp_path / "data")
    monkeypatch.setattr(
        "photofant.media.person_folders.materialize_assignment", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "photofant.media.person_folders.move_face_crops_to_person",
        lambda *args, **kwargs: None,
    )

    clustering_job.run_incremental_match(face.id)

    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []


def test_run_incremental_match_review_does_not_invalidate(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    _seed_recommendation(db_session, source_id=100, target_id=200)

    target_person = Person(name="Target", is_unknown=False)
    db_session.add(target_person)
    db_session.flush()

    face = Face(asset_id=100, person_id=1, crop_path="unused.jpg")
    db_session.add(face)
    db_session.commit()

    monkeypatch.setattr(clustering_job, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(
        engine,
        "match_face_incremental",
        lambda session, face_id: MatchResult(
            person_id=target_person.id, score=0.5, band="review"
        ),
    )

    clustering_job.run_incremental_match(face.id)

    assert len(db_session.query(Recommendation).filter_by(source_asset_id=100).all()) == 1
