"""REST-Layer der Aufgaben-Queue + Lookup-Trigger (P23 Phase 1)."""
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
        f"sqlite:///{tmp_path / 'knowledge_tasks.sqlite'}",
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


@pytest.mark.asyncio
async def test_create_task_returns_201(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/knowledge/tasks", json={"kind": "missing_entity", "context": {"ref": "actors/x"}}
        )

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "missing_entity"
    assert body["status"] == "open"
    assert body["context"] == {"ref": "actors/x"}


@pytest.mark.asyncio
async def test_create_task_unknown_kind_returns_422(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/knowledge/tasks", json={"kind": "not_a_kind"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_tasks_filters_by_status(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/knowledge/tasks", json={"kind": "missing_entity", "context": {"ref": "a"}}
        )
        task_id = created.json()["id"]
        await client.post(f"/api/knowledge/tasks/{task_id}/resolve")

        open_response = await client.get("/api/knowledge/tasks", params={"status": "open"})
        resolved_response = await client.get("/api/knowledge/tasks", params={"status": "resolved"})

    assert open_response.json() == []
    assert len(resolved_response.json()) == 1
    assert resolved_response.json()[0]["id"] == task_id


@pytest.mark.asyncio
async def test_resolve_task_marks_resolved(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/knowledge/tasks", json={"kind": "missing_entity", "context": {"ref": "a"}}
        )
        task_id = created.json()["id"]
        response = await client.post(f"/api/knowledge/tasks/{task_id}/resolve")

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_dismiss_task_marks_dismissed(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/knowledge/tasks", json={"kind": "missing_entity", "context": {"ref": "a"}}
        )
        task_id = created.json()["id"]
        response = await client.post(f"/api/knowledge/tasks/{task_id}/dismiss")

    assert response.status_code == 200
    assert response.json()["status"] == "dismissed"


@pytest.mark.asyncio
async def test_resolve_unknown_task_returns_404(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/knowledge/tasks/999/resolve")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_resolve_task_twice_returns_409(app_with_deps: tuple[Any, Session, Vault]) -> None:
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/knowledge/tasks", json={"kind": "missing_entity", "context": {"ref": "a"}}
        )
        task_id = created.json()["id"]
        await client.post(f"/api/knowledge/tasks/{task_id}/resolve")
        response = await client.post(f"/api/knowledge/tasks/{task_id}/resolve")

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_lookup_endpoint_returns_job_id(app_with_deps: tuple[Any, Session, Vault]) -> None:
    """Nur der Trigger selbst: der eigentliche Job-Lauf (Dedup, Vault-Lookup) ist in
    `test_knowledge_lookup_job.py` an `_run_lookup` direkt getestet, nicht über die
    Queue — der reale `job_queue` ist ein Modul-Singleton (kein Worker läuft in Tests),
    ein hier enqueueter Job bliebe sonst unverarbeitet zwischen Testläufen liegen
    (gleiches Muster wie die anderen Job-Trigger-Endpoints, z.B. `/maintenance/reconcile`)."""
    app, _session, _vault = app_with_deps

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/knowledge/lookup", json={"kind": "missing_entity", "ref": "actors/nobody"}
        )

    assert response.status_code == 200
    assert "job_id" in response.json()
