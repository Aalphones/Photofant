"""Einstellungen › KI (P27/P38) — GET/PATCH der Autonomie-Stufen je KI-Funktion. Deckt den
Web-Recherche-Schalter ab, der zuvor nur per Hand in settings.json erreichbar war."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from photofant.main import create_app


@pytest.fixture
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[AsyncClient, None, None]:
    # Eigene settings.json pro Test — nie die echte Nutzer-Konfiguration anfassen.
    monkeypatch.setenv("PHOTOFANT_SETTINGS_PATH", str(tmp_path / "settings.json"))
    app = create_app()
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_get_autonomy_returns_defaults(app_client: AsyncClient) -> None:
    async with app_client as client:
        response = await client.get("/api/knowledge/ai/autonomy")
        assert response.status_code == 200
        body = response.json()
        assert body["discovery"] == "off"
        assert body["knowledge_import"] == "ask"


@pytest.mark.asyncio
async def test_patch_autonomy_updates_single_field_and_persists(app_client: AsyncClient) -> None:
    async with app_client as client:
        response = await client.patch("/api/knowledge/ai/autonomy", json={"discovery": "auto"})
        assert response.status_code == 200
        assert response.json()["discovery"] == "auto"

        # Andere Felder bleiben unangetastet (deep-merge, kein Überschreiben des ganzen Blocks)
        follow_up = await client.get("/api/knowledge/ai/autonomy")
        body = follow_up.json()
        assert body["discovery"] == "auto"
        assert body["knowledge_import"] == "ask"


@pytest.mark.asyncio
async def test_patch_autonomy_rejects_ask_for_discovery(app_client: AsyncClient) -> None:
    async with app_client as client:
        response = await client.patch("/api/knowledge/ai/autonomy", json={"discovery": "ask"})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_autonomy_rejects_unknown_mode(app_client: AsyncClient) -> None:
    async with app_client as client:
        response = await client.patch("/api/knowledge/ai/autonomy", json={"interview": "yolo"})
        assert response.status_code == 422
