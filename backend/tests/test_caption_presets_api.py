"""Caption-preset CRUD endpoint — validation against caption_mode + default handling."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import Base, CaptionPreset, ModelRegistry
from photofant.db.session import get_session
from photofant.main import create_app


@pytest.fixture
def app_with_db(tmp_path: Path) -> Generator[tuple[Any, Session], None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'presets.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add(ModelRegistry(
        manifest_id="florence-2-base", role="captioner", name="Florence-2 Base",
        caption_mode="task_token", enabled=True,
    ))
    session.commit()

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
async def test_create_validates_and_normalizes_config(app_with_db: tuple[Any, Session]) -> None:
    app, _ = app_with_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/caption-presets",
            json={"name": "Mein Preset", "config": {"task_token": "<CAPTION>"}},
        )
    assert response.status_code == 201
    body = response.json()
    # Defaults filled in by validation.
    assert body["config"] == {"task_token": "<CAPTION>", "max_new_tokens": 1024, "num_beams": 3}


@pytest.mark.asyncio
async def test_create_rejects_invalid_task_token(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/caption-presets",
            json={"name": "Kaputt", "config": {"task_token": "<NOPE>"}},
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNKNOWN_TASK_TOKEN"
    assert session.query(CaptionPreset).count() == 0


@pytest.mark.asyncio
async def test_setting_default_clears_previous_default(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(
            "/api/caption-presets",
            json={"name": "A", "config": {"task_token": "<CAPTION>"}, "is_default": True},
        )
        second = await client.post(
            "/api/caption-presets",
            json={"name": "B", "config": {"task_token": "<DETAILED_CAPTION>"}, "is_default": True},
        )

    first_id = first.json()["id"]
    second_id = second.json()["id"]
    session.expire_all()
    assert session.get(CaptionPreset, first_id).is_default is False
    assert session.get(CaptionPreset, second_id).is_default is True


@pytest.mark.asyncio
async def test_delete_removes_preset(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/caption-presets",
            json={"name": "Weg damit", "config": {"task_token": "<CAPTION>"}},
        )
        preset_id = created.json()["id"]
        deleted = await client.delete(f"/api/caption-presets/{preset_id}")

    assert deleted.status_code == 204
    assert session.query(CaptionPreset).count() == 0
