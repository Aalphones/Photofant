"""REST-Layer der Wissensbasis (P22 Phase 3) — Routing, Statuscodes, Ownership über HTTP."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import Asset, Base, Face, Person
from photofant.db.session import get_session
from photofant.knowledge.changelog import ChangelogService
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
async def test_create_entity_persists_body_as_markdown(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/knowledge/entities", json=_entity_payload(body="Bekannt für die Iron-Man-Reihe.")
        )

    assert response.status_code == 201
    assert response.json()["body"] == "Bekannt für die Iron-Man-Reihe."
    markdown = (vault.root / "actors" / "robert-downey-jr.md").read_text(encoding="utf-8")
    assert "Bekannt für die Iron-Man-Reihe." in markdown


@pytest.mark.asyncio
async def test_create_entity_persists_attributes_with_own_owner(
    app_with_deps: tuple[Any, Session, Vault]
) -> None:
    """AK 1 Phase 3: Entity-Owner bleibt ``user``, jedes Merkmal behält seinen eigenen Owner."""
    app, _session, vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/knowledge/entities",
            json=_entity_payload(
                attributes={
                    "geburtstag": {"value": "4. April 1965", "owner": "user", "confidence": 1.0},
                    "geburtsort": {"value": "New York City", "owner": "inferred", "confidence": 0.6},
                }
            ),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["owner"] == "user"
    assert body["completeness"] > 0
    assert body["attributes"]["geburtstag"] == {
        "value": "4. April 1965", "owner": "user", "confidence": 1.0,
    }
    assert body["attributes"]["geburtsort"]["owner"] == "inferred"
    markdown = (vault.root / "actors" / "robert-downey-jr.md").read_text(encoding="utf-8")
    assert "geburtstag" in markdown


@pytest.mark.asyncio
async def test_list_domains_returns_seeded_domains(
    app_with_deps: tuple[Any, Session, Vault]
) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/knowledge/domains")

    assert response.status_code == 200
    domains = response.json()
    by_name = {domain["name"]: domain for domain in domains}
    # Zwei mitgelieferte Domänen seit P27 Phase 4: die öffentliche „Movies" und die als
    # privat markierte „Private" (Interview-Mode, Konzept-ADR-009).
    assert {"Movies", "Private"} <= set(by_name)

    movies = by_name["Movies"]
    assert movies["private"] is False
    assert {entity_type["name"] for entity_type in movies["entity_types"]} >= {"Actor", "Movie"}
    assert "plays" in movies["relationship_types"]

    private = by_name["Private"]
    assert private["private"] is True
    assert {entity_type["name"] for entity_type in private["entity_types"]} >= {"Person", "Pet"}


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
    lore_body = lore.json()
    assert lore_body["entity"]["id"] == "actors/robert-downey-jr"
    assert lore_body["relationships"] == [
        {
            "type": "plays",
            "target": {
                "id": "movies/iron-man",
                "title": "Iron Man",
                "type": "Movie",
                "completeness": 0.0,
            },
        }
    ]
    assert lore_body["franchises"] == []
    assert lore_body["related_media"] == []
    assert lore_body["sources"] == []
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


@pytest.mark.asyncio
async def test_lore_by_person_id_without_link_returns_200_with_empty_list(
    app_with_deps: tuple[Any, Session, Vault],
) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/knowledge/lore", params={"person_id": 42})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_lore_by_person_id_resolves_linked_entity_and_media(
    app_with_deps: tuple[Any, Session, Vault],
) -> None:
    app, session, _vault = app_with_deps
    session.add(Person(id=42, name="Robert Downey Jr.", is_unknown=False))
    session.add(Face(id=7, person_id=42, crop_path="x", score=0.9))
    session.add(Asset(id=99, content_hash="abc"))
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/knowledge/entities",
            json=_entity_payload(media_links={"persons": [42], "assets": [99]}),
        )
        response = await client.get("/api/knowledge/lore", params={"person_id": 42})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    block = body[0]
    assert block["entity"]["id"] == "actors/robert-downey-jr"
    assert {ref["kind"]: ref["id"] for ref in block["related_media"]} == {"person": 42, "asset": 99}
    person_ref = next(ref for ref in block["related_media"] if ref["kind"] == "person")
    assert person_ref["thumbnail_url"] == "/api/faces/7/thumbnail"
    asset_ref = next(ref for ref in block["related_media"] if ref["kind"] == "asset")
    assert asset_ref["thumbnail_url"] == "/api/assets/99/thumbnail"


@pytest.mark.asyncio
async def test_lore_requires_exactly_one_of_asset_id_or_person_id(
    app_with_deps: tuple[Any, Session, Vault],
) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        neither = await client.get("/api/knowledge/lore")
        both = await client.get("/api/knowledge/lore", params={"asset_id": 1, "person_id": 2})

    assert neither.status_code == 422
    assert both.status_code == 422


@pytest.mark.asyncio
async def test_patch_correction_endpoint_returns_job_id(app_with_deps: tuple[Any, Session, Vault]) -> None:
    """Nur der Trigger selbst: der eigentliche Job-Lauf (Ownership, Changelog-Eintrag) ist
    in `test_knowledge_patch_job.py` an `_run_patch` direkt getestet, nicht über die Queue —
    gleiches Muster wie `test_lookup_endpoint_returns_job_id` in `test_knowledge_tasks_api.py`."""
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/knowledge/entities", json=_entity_payload())
        response = await client.post(
            "/api/knowledge/entities/actors/robert-downey-jr/patch",
            json={"field": "body", "value": "Neuer Text.", "reason": "Das stimmt nicht"},
        )

    assert response.status_code == 200
    assert "job_id" in response.json()


@pytest.mark.asyncio
async def test_patch_correction_unknown_field_returns_422(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/knowledge/entities/actors/robert-downey-jr/patch",
            json={"field": "owner", "value": "user", "reason": "x"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_changelog_returns_entries_for_entity(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/knowledge/entities", json=_entity_payload())
        ChangelogService(session).record(
            entity_id="actors/robert-downey-jr",
            field="body",
            old_value="alt",
            new_value="neu",
            reason="Das stimmt nicht",
            source="user",
            job_id="job-x",
        )
        session.commit()

        response = await client.get("/api/knowledge/entities/actors/robert-downey-jr/changelog")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["field"] == "body"
    assert body[0]["old_value"] == "alt"
    assert body[0]["new_value"] == "neu"
    assert body[0]["reason"] == "Das stimmt nicht"
    assert body[0]["source"] == "user"
    assert body[0]["job_id"] == "job-x"
