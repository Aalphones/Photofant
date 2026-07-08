"""REST-Layer der Wissensbasis (P22 Phase 3) — Routing, Statuscodes, Ownership über HTTP."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import Base
from photofant.db.session import get_session
from photofant.knowledge.vault import Vault, open_vault
from photofant.main import create_app


@pytest.fixture
def app_with_deps(tmp_path: Path) -> Generator[tuple[Any, Session, Vault], None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'knowledge.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()

    vault = Vault(tmp_path / "vault")
    vault.ensure_structure()

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


def _entity_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "actors/robert-downey-jr",
        "type": "Actor",
        "title": "Robert Downey Jr.",
        "domain": "Movies",
        "aliases": ["RDJ"],
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_create_entity_returns_201_and_persists(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/knowledge/entities", json=_entity_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "actors/robert-downey-jr"
    assert body["owner"] == "user"
    assert body["confidence"] == 1.0
    assert (vault.root / "actors" / "robert-downey-jr.md").exists()


@pytest.mark.asyncio
async def test_create_entity_conflict_on_duplicate(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/knowledge/entities", json=_entity_payload())
        response = await client.post("/api/knowledge/entities", json=_entity_payload())

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_entity_unknown_type_returns_422(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/knowledge/entities", json=_entity_payload(id="aliens/xenomorph", type="Alien")
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_entity_by_id_and_alias(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/knowledge/entities", json=_entity_payload())

        by_id = await client.get("/api/knowledge/entities/actors/robert-downey-jr")
        by_alias = await client.get("/api/knowledge/entities/RDJ")
        missing = await client.get("/api/knowledge/entities/actors/nobody")

    assert by_id.status_code == 200
    assert by_alias.status_code == 200
    assert by_id.json()["id"] == by_alias.json()["id"] == "actors/robert-downey-jr"
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_search_finds_entity_via_alias(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/knowledge/entities", json=_entity_payload())
        response = await client.get("/api/knowledge/entities/search", params={"q": "RDJ"})

    assert response.status_code == 200
    results = response.json()
    assert [entity["id"] for entity in results] == ["actors/robert-downey-jr"]


@pytest.mark.asyncio
async def test_patch_updates_entity(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/knowledge/entities", json=_entity_payload())
        response = await client.patch(
            "/api/knowledge/entities/actors/robert-downey-jr", json={"status": "active"}
        )

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    on_disk = vault.load_entity(vault.root / "actors" / "robert-downey-jr.md")
    assert on_disk.status == "active"


@pytest.mark.asyncio
async def test_patch_with_lower_priority_owner_is_rejected(
    app_with_deps: tuple[Any, Session, Vault],
) -> None:
    """Plan-Smoke-Checkliste #4: PATCH mit owner=inferred auf ein user-Feld wird abgelehnt."""
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/knowledge/entities", json=_entity_payload())  # owner=user (Default)
        response = await client.patch(
            "/api/knowledge/entities/actors/robert-downey-jr",
            json={"status": "should-not-apply", "owner": "inferred"},
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_patch_missing_entity_returns_404(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/knowledge/entities/actors/nobody", json={"status": "active"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_entity_removes_file(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/knowledge/entities", json=_entity_payload())
        response = await client.delete("/api/knowledge/entities/actors/robert-downey-jr")
        missing = await client.get("/api/knowledge/entities/actors/robert-downey-jr")

    assert response.status_code == 204
    assert missing.status_code == 404
    assert not (vault.root / "actors" / "robert-downey-jr.md").exists()


@pytest.mark.asyncio
async def test_relationship_lifecycle_and_lore(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/knowledge/entities", json=_entity_payload())
        await client.post(
            "/api/knowledge/entities",
            json=_entity_payload(id="movies/iron-man", type="Movie", title="Iron Man", aliases=[]),
        )

        created = await client.post(
            "/api/knowledge/entities/actors/robert-downey-jr/relationships",
            json={"type": "plays", "target": "movies/iron-man"},
        )
        lore = await client.get("/api/knowledge/entities/actors/robert-downey-jr/lore")
        removed = await client.request(
            "DELETE",
            "/api/knowledge/entities/actors/robert-downey-jr/relationships",
            params={"type": "plays", "target": "movies/iron-man"},
        )

    assert created.status_code == 200
    assert created.json()["relationships"] == [{"type": "plays", "target": "movies/iron-man"}]
    assert lore.status_code == 200
    assert lore.json()["relationships"] == [{"type": "plays", "target": "movies/iron-man"}]
    assert removed.status_code == 200
    assert removed.json()["relationships"] == []


@pytest.mark.asyncio
async def test_relationship_unknown_type_returns_422(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/knowledge/entities", json=_entity_payload())
        response = await client.post(
            "/api/knowledge/entities/actors/robert-downey-jr/relationships",
            json={"type": "not_a_real_type", "target": "movies/iron-man"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_lore_missing_entity_returns_404(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/knowledge/entities/actors/nobody/lore")

    assert response.status_code == 404
