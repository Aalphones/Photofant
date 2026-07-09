"""REST-Layer der Empfehlungen (P26 Phase 1) — Cache-Treffer, Cache-Fehltreffer plant den
Job, abgeschaltet, und „Warum nicht?"."""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.api import recommendations as recommendations_api
from photofant.db.models import (
    Asset,
    AssetInstance,
    Base,
    KnowledgeEntity,
    KnowledgeMediaLink,
    KnowledgeRelationship,
    Person,
    Recommendation,
)
from photofant.db.session import get_session
from photofant.main import create_app


def _settings(**overrides: Any) -> dict[str, Any]:
    recommendations: dict[str, Any] = {
        "enabled": True,
        "max_results": 12,
        "min_score": 0.3,
        "weights": {
            "same_person": 0.4,
            "same_role": 0.25,
            "same_film": 0.15,
            "clip_similarity": 0.2,
        },
    }
    recommendations.update(overrides)
    return {"recommendations": recommendations}


@pytest.fixture
def app_with_session(tmp_path: Path) -> Generator[tuple[Any, Session], None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'reco.sqlite'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add(Person(id=1, name="_unknown", is_unknown=True))
    session.commit()

    app = create_app()

    def _session_override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = _session_override
    try:
        yield app, session
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def _client(app: Any) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _seed_pair(session: Session) -> None:
    """Quelle 100 + Kandidat 101 teilen Person (RDJ) und Rolle (Tony Stark)."""
    session.add(Person(id=10, name="Robert Downey Jr.", is_unknown=False))
    session.add(Asset(id=100, content_hash="hash-100"))
    session.add(Asset(id=101, content_hash="hash-101"))
    session.add(Asset(id=103, content_hash="hash-103"))
    session.add(AssetInstance(asset_id=100, person_id=10, path="/library/100.jpg"))
    session.add(AssetInstance(asset_id=101, person_id=10, path="/library/101.jpg"))
    session.add(AssetInstance(asset_id=103, person_id=1, path="/library/103.jpg"))
    session.add(
        KnowledgeEntity(
            id="characters/tony-stark", type="Character", title="Tony Stark",
            domain="Movies", owner="user", status="",
        )
    )
    session.add(
        KnowledgeEntity(
            id="movies/iron-man", type="Movie", title="Iron Man",
            domain="Movies", owner="user", status="",
        )
    )
    session.add(KnowledgeMediaLink(entity_id="characters/tony-stark", kind="person", target_id=10))
    session.add(
        KnowledgeRelationship(
            entity_id="characters/tony-stark", type="appears_in", target="movies/iron-man"
        )
    )
    session.commit()


@pytest.mark.asyncio
async def test_get_recommendations_returns_cached_rows(
    app_with_session: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, session = app_with_session
    monkeypatch.setattr(recommendations_api, "load_settings", lambda: _settings())
    _seed_pair(session)
    session.add(
        Recommendation(
            source_asset_id=100,
            recommended_asset_id=101,
            score=0.65,
            reasons=[{"signal": "same_person", "detail": "Robert Downey Jr.", "weight": 0.4}],
            computed_at=datetime.utcnow(),
        )
    )
    session.commit()

    async with _client(app) as client:
        response = await client.get("/api/recommendations", params={"asset_id": 100})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert len(body["recommendations"]) == 1
    card = body["recommendations"][0]
    assert card["asset_id"] == 101
    assert card["thumbnail_url"] == "/api/assets/101/thumbnail"
    assert card["reasons"][0]["signal"] == "same_person"


@pytest.mark.asyncio
async def test_get_recommendations_schedules_job_on_cache_miss(
    app_with_session: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, session = app_with_session
    monkeypatch.setattr(recommendations_api, "load_settings", lambda: _settings())
    _seed_pair(session)

    scheduled: list[int] = []

    async def _fake_enqueue(source_asset_id: int) -> None:
        scheduled.append(source_asset_id)

    monkeypatch.setattr(recommendations_api, "enqueue_recommendation", _fake_enqueue)

    async with _client(app) as client:
        response = await client.get("/api/recommendations", params={"asset_id": 100})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "computing"
    assert body["recommendations"] == []
    assert scheduled == [100]


@pytest.mark.asyncio
async def test_get_recommendations_disabled_returns_no_job(
    app_with_session: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, session = app_with_session
    monkeypatch.setattr(recommendations_api, "load_settings", lambda: _settings(enabled=False))

    async def _fail_enqueue(source_asset_id: int) -> None:
        raise AssertionError("enqueue darf bei abgeschalteten Empfehlungen nicht laufen")

    monkeypatch.setattr(recommendations_api, "enqueue_recommendation", _fail_enqueue)

    async with _client(app) as client:
        response = await client.get("/api/recommendations", params={"asset_id": 100})

    assert response.json()["status"] == "disabled"


@pytest.mark.asyncio
async def test_why_not_explains_present_and_missing_signals(
    app_with_session: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, session = app_with_session
    monkeypatch.setattr(recommendations_api, "load_settings", lambda: _settings())
    _seed_pair(session)

    async with _client(app) as client:
        response = await client.get("/api/recommendations/100/101/why-not")

    assert response.status_code == 200
    body = response.json()
    assert body["recommended"] is True
    assert body["threshold"] == 0.3
    # Dieselbe Figur im selben Film → Person + Rolle + Film. CLIP fehlt (kein Embedding in der Test-DB).
    present = {reason["signal"] for reason in body["reasons"]}
    assert present == {"same_person", "same_role", "same_film"}
    missing = {reason["signal"] for reason in body["missing"]}
    assert missing == {"clip"}


@pytest.mark.asyncio
async def test_why_not_for_unrelated_target_lists_all_signals_missing(
    app_with_session: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, session = app_with_session
    monkeypatch.setattr(recommendations_api, "load_settings", lambda: _settings())
    _seed_pair(session)

    async with _client(app) as client:
        response = await client.get("/api/recommendations/100/103/why-not")

    body = response.json()
    assert body["recommended"] is False
    assert body["reasons"] == []
    assert {reason["signal"] for reason in body["missing"]} == {
        "same_person", "same_role", "same_film", "clip",
    }
