"""Face-Detail-Endpoint (P15 Phase 7 — Gesichter-Modus der Lightbox).

GET /api/faces/{id} liefert Face-Detail + eigene Versionen + Source-Asset-Link,
Grundlage für den Gesichter-Modus der Lightbox (Editor läuft weiter auf
photofant.api.assets — hier nur der neue Detail-Endpunkt).
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import Asset, Base, Face, Person, Version
from photofant.db.session import get_session
from photofant.main import create_app


@pytest.fixture
def app_with_db(tmp_path: Path) -> Generator[tuple[Any, Session], None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'faces.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()

    app = create_app()

    def _override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = _override
    try:
        yield app, session
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_get_face_returns_detail_with_versions_and_source(
    app_with_db: tuple[Any, Session],
) -> None:
    app, session = app_with_db

    person = Person(name="Sascha", is_unknown=False)
    session.add(person)
    session.flush()

    asset = Asset(content_hash="abc123", created_at=datetime.now(UTC).replace(tzinfo=None))
    session.add(asset)
    session.flush()

    face = Face(
        asset_id=asset.id,
        person_id=person.id,
        crop_path="/tmp/face.jpg",
        score=0.87,
        age=30,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(face)
    session.flush()

    version = Version(
        face_id=face.id,
        type="crop",
        path="/tmp/face_v1.jpg",
        is_current=True,
        params={"width": 512, "height": 512},
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(version)
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/faces/{face.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == face.id
    assert body["person_id"] == person.id
    assert body["person_name"] == "Sascha"
    assert body["source_asset_id"] == asset.id
    assert body["crop_url"] == f"/faces/{face.id}/thumbnail"
    assert len(body["versions"]) == 1
    assert body["versions"][0]["id"] == version.id
    assert body["versions"][0]["is_current"] is True
    assert body["versions"][0]["res"] == {"width": 512, "height": 512}


@pytest.mark.asyncio
async def test_get_face_without_person_or_versions(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db

    face = Face(
        asset_id=None,
        person_id=None,
        crop_path="/tmp/face.jpg",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(face)
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/faces/{face.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["person_id"] is None
    assert body["person_name"] is None
    assert body["source_asset_id"] is None
    assert body["versions"] == []


@pytest.mark.asyncio
async def test_get_face_404_for_unknown_id(app_with_db: tuple[Any, Session]) -> None:
    app, _ = app_with_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/faces/999999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_faces_gallery_route_still_matches_before_detail_route(
    app_with_db: tuple[Any, Session],
) -> None:
    """`/faces/gallery` must not be shadowed by the newly added `/faces/{face_id}`."""
    app, _ = app_with_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/faces/gallery")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
