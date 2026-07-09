"""`/api/assets/{id}/link-entity` — Asset↔Entity-Verknüpfung über REST (P24 Phase 1)."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import Asset, AssetInstance, Base, Person
from photofant.db.session import get_session
from photofant.knowledge.schema import Entity, Owner
from photofant.knowledge.service import KnowledgeService
from photofant.knowledge.vault import Vault, open_vault
from photofant.main import create_app


@pytest.fixture
def app_with_deps(tmp_path: Path) -> Generator[tuple[Any, Session, Vault], None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'assets.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()

    vault = Vault(tmp_path / "vault")
    vault.ensure_structure()
    KnowledgeService(session, vault).create_entity(
        Entity(id="movies/iron-man", type="Movie", title="Iron Man", domain="Movies"), Owner.USER
    )

    person = Person(id=1, name="_unknown", is_unknown=True)
    asset = Asset(id=7, content_hash="hash-7")
    session.add_all([person, asset])
    session.flush()
    session.add(AssetInstance(asset_id=7, person_id=1, path="asset-7.jpg"))
    session.commit()

    app = create_app()

    def _session_override() -> Generator[Session, None, None]:
        yield session

    def _vault_override() -> Vault:
        return vault

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[open_vault] = _vault_override
    try:
        yield app, session, vault
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_link_entity_sets_linked_entity_on_asset_detail(
    app_with_deps: tuple[Any, Session, Vault]
) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/assets/7/link-entity", json={"entity_id": "movies/iron-man"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["linked_entity"] == {"id": "movies/iron-man", "title": "Iron Man", "type": "Movie"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        detail = await client.get("/api/assets/7")
    assert detail.json()["linked_entity"]["id"] == "movies/iron-man"


@pytest.mark.asyncio
async def test_unlink_entity_clears_linked_entity_on_asset(
    app_with_deps: tuple[Any, Session, Vault]
) -> None:
    app, session, vault = app_with_deps
    KnowledgeService(session, vault).link_media("movies/iron-man", "asset", 7, Owner.USER)
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(
            "DELETE", "/api/assets/7/link-entity", params={"entity_id": "movies/iron-man"}
        )

    assert response.status_code == 200
    assert response.json()["linked_entity"] is None


@pytest.mark.asyncio
async def test_link_entity_unknown_asset_returns_404(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/assets/999/link-entity", json={"entity_id": "movies/iron-man"}
        )

    assert response.status_code == 404
