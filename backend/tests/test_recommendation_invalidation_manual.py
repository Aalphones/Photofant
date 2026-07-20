"""Recommendation-Cache-Invalidierung bei manuellen Face-/Person-Aktionen (Phase 2 des
Plans ``2026-07-20_recommendation-cache-invalidation``).

Testet nur, dass ``invalidate_recommendations`` an jeder Call-Site mit den richtigen
Asset-IDs vor dem Commit aufgerufen wird — die physischen Datei-Operationen
(``reassign_face``, ``merge_persons``, ``split_faces``, ...) sind bereits in
``test_person_folders.py`` abgedeckt und laufen hier ohne echte Dateien defensiv
durch (alle Move-Helper schlucken ``FileNotFoundError``/fehlende Quell-Instanzen).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm import Session

from photofant.api import faces as faces_api
from photofant.api import persons as persons_api
from photofant.api import review_queue as review_queue_api
from photofant.api.faces import AssignRequest
from photofant.api.persons import MergeRequest, SplitRequest
from photofant.api.review_queue import ReviewActionRequest
from photofant.db.models import Asset, AssetInstance, Face, Person, Recommendation, ReviewItem
from photofant.jobs.bulk_assign_person_job import _assign_one_asset


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


@pytest.mark.asyncio
async def test_assign_face_invalidates_cache_for_reassigned_asset(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("photofant.config.get_data_root", lambda: tmp_path / "data")
    monkeypatch.setattr(
        "photofant.jobs.collections_job.enqueue_reevaluate_assets", AsyncMock(return_value=None)
    )

    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    _seed_recommendation(db_session, source_id=100, target_id=200)

    target_person = Person(name="Target", is_unknown=False)
    db_session.add(target_person)
    db_session.flush()
    face = Face(asset_id=100, person_id=1, crop_path=str(tmp_path / "missing.jpg"))
    db_session.add(face)
    db_session.commit()

    await faces_api.assign_face(face.id, AssignRequest(person_id=target_person.id), db_session)

    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []


@pytest.mark.asyncio
async def test_assign_face_invalidates_cache_row_where_asset_is_only_the_target(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kern-Fix aus Phase 1 im echten Aufrufkontext: das reassignte Asset (100) taucht in
    der Cache-Zeile nur als ``recommended_asset_id`` auf, nicht als Quelle — muss trotzdem
    verschwinden."""
    monkeypatch.setattr("photofant.config.get_data_root", lambda: tmp_path / "data")
    monkeypatch.setattr(
        "photofant.jobs.collections_job.enqueue_reevaluate_assets", AsyncMock(return_value=None)
    )

    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    _seed_recommendation(db_session, source_id=200, target_id=100)

    target_person = Person(name="Target", is_unknown=False)
    db_session.add(target_person)
    db_session.flush()
    face = Face(asset_id=100, person_id=1, crop_path=str(tmp_path / "missing.jpg"))
    db_session.add(face)
    db_session.commit()

    await faces_api.assign_face(face.id, AssignRequest(person_id=target_person.id), db_session)

    assert db_session.query(Recommendation).filter_by(source_asset_id=200).all() == []


@pytest.mark.asyncio
async def test_merge_persons_invalidates_cache_for_target_person_assets(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("photofant.config.get_data_root", lambda: tmp_path / "data")
    monkeypatch.setattr(
        "photofant.jobs.collections_job.enqueue_reevaluate_assets", AsyncMock(return_value=None)
    )

    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    _seed_recommendation(db_session, source_id=100, target_id=200)

    from_person = Person(name="From", is_unknown=False)
    into_person = Person(name="Into", is_unknown=False)
    db_session.add_all([from_person, into_person])
    db_session.flush()
    db_session.add(
        AssetInstance(asset_id=100, person_id=into_person.id, path=str(tmp_path / "100.jpg"))
    )
    db_session.commit()

    await persons_api.merge_persons_endpoint(
        MergeRequest(from_id=from_person.id, into_id=into_person.id), db_session
    )

    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []


@pytest.mark.asyncio
async def test_split_person_returns_asset_ids_and_invalidates_cache(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("photofant.config.get_data_root", lambda: tmp_path / "data")
    monkeypatch.setattr(
        "photofant.jobs.collections_job.enqueue_reevaluate_assets", AsyncMock(return_value=None)
    )

    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    _seed_recommendation(db_session, source_id=100, target_id=200)

    source_person = Person(name="Source", is_unknown=False)
    db_session.add(source_person)
    db_session.flush()
    face = Face(asset_id=100, person_id=source_person.id, crop_path=str(tmp_path / "missing.jpg"))
    db_session.add(face)
    db_session.commit()

    result = await persons_api.split_person(
        source_person.id, SplitRequest(face_ids=[face.id]), db_session
    )

    assert result.new_person_id is not None
    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []


@pytest.mark.asyncio
async def test_resolve_face_review_confirm_invalidates_cache(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("photofant.config.get_data_root", lambda: tmp_path / "data")
    monkeypatch.setattr(
        "photofant.jobs.collections_job.enqueue_reevaluate_assets", AsyncMock(return_value=None)
    )
    monkeypatch.setattr("photofant.knowledge.vault.open_vault", lambda: object())
    monkeypatch.setattr(
        "photofant.settings.load_settings", lambda: {"knowledge": {"auto_lookup": False}}
    )

    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    _seed_recommendation(db_session, source_id=100, target_id=200)

    target_person = Person(name="Target", is_unknown=False)
    db_session.add(target_person)
    db_session.flush()
    face = Face(asset_id=100, person_id=1, crop_path=str(tmp_path / "missing.jpg"))
    db_session.add(face)
    db_session.flush()
    item = ReviewItem(
        type="face_suggestion",
        asset_a_id=100,
        asset_b_id=100,
        face_id=face.id,
        suggested_person_id=target_person.id,
        created_at=datetime.utcnow(),
        resolved_at=None,
        score=0.9,
    )
    db_session.add(item)
    db_session.commit()

    result = await review_queue_api.resolve_face_review(
        face.id, ReviewActionRequest(action="confirm"), db_session
    )

    assert result == {"status": "confirmed"}
    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []


def test_bulk_assign_one_asset_invalidates_cache(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_assign_one_asset`` öffnet seine eigene Session über ``SessionLocal`` (Job-Muster) —
    hier auf die Test-Session umgebogen, analog zu ``test_dupe_scan_dino.py``."""
    import photofant.jobs.bulk_assign_person_job as bulk_assign_person_job

    monkeypatch.setattr(bulk_assign_person_job, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    _add_asset(db_session, 100)
    target_person = Person(name="Target", is_unknown=False)
    db_session.add(target_person)
    db_session.flush()
    unknown_photo = tmp_path / "unknown_100.jpg"
    unknown_photo.write_bytes(b"image-bytes")
    db_session.add(
        AssetInstance(asset_id=100, person_id=1, path=str(unknown_photo))
    )
    _seed_recommendation(db_session, source_id=100, target_id=999)
    db_session.add(Asset(id=999, content_hash="hash-999"))
    db_session.commit()

    ok = _assign_one_asset(100, target_person.id, tmp_path / "data", unknown_person_id=1)

    assert ok is True
    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []
