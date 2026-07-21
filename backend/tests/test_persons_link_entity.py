"""`/api/persons/{id}/link-entity` — Person↔Entity-Verknüpfung über REST (P24 Phase 1)."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import Base, Person
from photofant.db.session import get_session
from photofant.knowledge.schema import Entity, Owner
from photofant.knowledge.service import KnowledgeService
from photofant.knowledge.vault import Vault, open_vault
from photofant.main import create_app


@pytest.fixture
def app_with_deps(tmp_path: Path) -> Generator[tuple[Any, Session, Vault], None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'persons.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()

    vault = Vault(tmp_path / "vault")
    vault.ensure_structure()
    KnowledgeService(session, vault).create_entity(
        Entity(id="actors/jane-doe", type="Actor", title="Jane Doe", domain="Movies"), Owner.USER
    )

    session.add(Person(id=1, name="_unknown", is_unknown=True))
    session.add(Person(id=42, name="Jane Doe", is_unknown=False))
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
async def test_link_entity_sets_linked_entity_on_person(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/persons/42/link-entity", json={"entity_id": "actors/jane-doe"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["linked_entity"] == {
        "id": "actors/jane-doe",
        "title": "Jane Doe",
        "type": "Actor",
        "completeness": 0.0,
    }


@pytest.mark.asyncio
async def test_list_persons_includes_linked_entity(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, session, vault = app_with_deps
    KnowledgeService(session, vault).link_media("actors/jane-doe", "person", 42, Owner.USER)
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/persons")

    assert response.status_code == 200
    persons = {row["id"]: row for row in response.json()}
    assert persons[42]["linked_entity"]["id"] == "actors/jane-doe"


@pytest.mark.asyncio
async def test_unlink_entity_clears_linked_entity(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, session, vault = app_with_deps
    KnowledgeService(session, vault).link_media("actors/jane-doe", "person", 42, Owner.USER)
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(
            "DELETE", "/api/persons/42/link-entity", params={"entity_id": "actors/jane-doe"}
        )

    assert response.status_code == 200
    assert response.json()["linked_entity"] is None


@pytest.mark.asyncio
async def test_link_entity_unknown_entity_returns_404(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/persons/42/link-entity", json={"entity_id": "actors/nobody"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_link_entity_unknown_person_returns_404(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/persons/999/link-entity", json={"entity_id": "actors/jane-doe"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_person_unlinks_orphaned_entity(
    app_with_deps: tuple[Any, Session, Vault], tmp_path: Path
) -> None:
    app, session, vault = app_with_deps
    KnowledgeService(session, vault).link_media("actors/jane-doe", "person", 42, Owner.USER)
    session.commit()

    with patch("photofant.config.get_data_root", return_value=tmp_path / "data"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/persons/42")

    assert response.status_code == 200
    entity = KnowledgeService(session, vault).find_entity("actors/jane-doe")
    assert entity is not None
    assert entity.media_links.persons == []
