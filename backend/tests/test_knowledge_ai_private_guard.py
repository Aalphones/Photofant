"""Privat/öffentlich-Trennung (Konzept-ADR-009, P27 Phase 4) — die private Domäne parst
als privat und der Web-Import-Pfad schließt sie aus."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from photofant.knowledge.vault import Vault
from photofant.main import create_app


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()  # seedet movies.yaml (öffentlich) + private.yaml (privat)
    return instance


def test_private_domain_parses_as_private(vault: Vault) -> None:
    assert vault.load_domain("Private").private is True
    assert vault.load_domain("Movies").private is False


def test_is_private_domain_helper(vault: Vault, monkeypatch: pytest.MonkeyPatch) -> None:
    from photofant.api import knowledge_ai

    monkeypatch.setattr(knowledge_ai, "open_vault", lambda: vault)
    assert knowledge_ai._is_private_domain("Private") is True
    assert knowledge_ai._is_private_domain("Movies") is False
    # Unbekannte/nicht ladbare Domäne ist nie „privat" (der Job validiert sie separat).
    assert knowledge_ai._is_private_domain("DoesNotExist") is False


@pytest.fixture
def app_client(vault: Vault, monkeypatch: pytest.MonkeyPatch) -> Generator[AsyncClient, None, None]:
    from photofant.api import knowledge_ai

    # Der Guard öffnet den Vault direkt (keine FastAPI-Dependency) — auf den Test-Vault umbiegen.
    monkeypatch.setattr(knowledge_ai, "open_vault", lambda: vault)
    app = create_app()
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_import_suggestion_rejects_private_domain(app_client: AsyncClient) -> None:
    async with app_client as client:
        response = await client.post(
            "/api/knowledge/ai/import-suggestion",
            json={"title": "Oma Erna", "domain": "Private", "type": "Person"},
        )
    assert response.status_code == 422
    assert "Interview" in response.json()["detail"]


@pytest.mark.asyncio
async def test_interview_rejects_public_domain(app_client: AsyncClient) -> None:
    async with app_client as client:
        response = await client.post(
            "/api/knowledge/ai/interview",
            json={"title": "Robert Downey Jr.", "domain": "Movies", "type": "Actor", "answers": []},
        )
    assert response.status_code == 422
