"""POST /api/search/by-image — upload-embed reverse search (P36 phase 1).

Covers the three AK cases from the phase plan: active embedder -> hits, no
embedder -> 409, unreadable upload -> 422. `vector_index.search` is mocked —
the throwaway test engine has no sqlite-vec extension wired in (same reason
test_assets_search.py never exercises the real vec0 table).
"""
from __future__ import annotations

import io
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.api import search as search_api
from photofant.db.models import Asset, AssetInstance, Base, Person
from photofant.db.session import get_session
from photofant.main import create_app
from photofant.settings import SETTINGS_DEFAULTS


@pytest.fixture
def app_with_db(tmp_path) -> Generator[tuple[Any, Session], None, None]:  # type: ignore[no-untyped-def]
    engine = create_engine(
        f"sqlite:///{tmp_path / 'assets.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add(Person(id=1, name="_unknown", is_unknown=True))
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


def _seed_asset(session: Session, *, content_hash: str) -> Asset:
    asset = Asset(content_hash=content_hash, source="original")
    session.add(asset)
    session.flush()
    session.add(AssetInstance(asset_id=asset.id, person_id=1, path=f"/tmp/{content_hash}.jpg"))
    session.commit()
    return asset


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def _patch_reverse_search_settings(monkeypatch: pytest.MonkeyPatch, **overrides: float | int) -> None:
    settings = {**SETTINGS_DEFAULTS["reverse_search"], **overrides}
    # Rerank off in these P36 tests — they assert the plain SigLIP2 order. Two-stage
    # re-ranking is covered separately in test_search_rerank.py.
    rerank = {**SETTINGS_DEFAULTS["rerank"], "enabled": False}
    monkeypatch.setattr(
        search_api, "load_settings", lambda: {"reverse_search": settings, "rerank": rerank}
    )


class _FakeEmbedder:
    dim = 4

    def embed(self, image: np.ndarray) -> np.ndarray:
        return np.zeros(self.dim, dtype=np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        return np.zeros(self.dim, dtype=np.float32)


@pytest.mark.asyncio
async def test_by_image_returns_hits_for_active_embedder(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, session = app_with_db
    asset = _seed_asset(session, content_hash="hit-1")
    _patch_reverse_search_settings(monkeypatch)
    monkeypatch.setattr(
        "photofant.inference.image_embedder.resolve_image_embedder", lambda: _FakeEmbedder(),
    )
    monkeypatch.setattr(
        search_api.vector_index, "search",
        lambda session, embedding, limit: [(asset.id, 0.9)],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/search/by-image", files={"file": ("upload.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["hits"] == [{"asset_id": asset.id, "score": 0.9}]


@pytest.mark.asyncio
async def test_by_image_excludes_soft_deleted_hits(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, session = app_with_db
    live = _seed_asset(session, content_hash="hit-live")
    deleted = _seed_asset(session, content_hash="hit-deleted")
    session.query(AssetInstance).filter_by(asset_id=deleted.id).update({"deleted_at": datetime.now(UTC)})
    session.commit()
    _patch_reverse_search_settings(monkeypatch)
    monkeypatch.setattr(
        "photofant.inference.image_embedder.resolve_image_embedder", lambda: _FakeEmbedder(),
    )
    monkeypatch.setattr(
        search_api.vector_index, "search",
        lambda session, embedding, limit: [(deleted.id, 0.95), (live.id, 0.8)],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/search/by-image", files={"file": ("upload.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["hits"] == [{"asset_id": live.id, "score": 0.8}]


@pytest.mark.asyncio
async def test_by_image_without_active_embedder_returns_409(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _session = app_with_db
    _patch_reverse_search_settings(monkeypatch)
    monkeypatch.setattr("photofant.inference.image_embedder.resolve_image_embedder", lambda: None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/search/by-image", files={"file": ("upload.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SEMANTIC_SEARCH_UNAVAILABLE"


@pytest.mark.asyncio
async def test_by_image_with_unreadable_upload_returns_422(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _session = app_with_db
    _patch_reverse_search_settings(monkeypatch)
    monkeypatch.setattr(
        "photofant.inference.image_embedder.resolve_image_embedder", lambda: _FakeEmbedder(),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/search/by-image", files={"file": ("upload.txt", b"not an image", "text/plain")},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_IMAGE"


@pytest.mark.asyncio
async def test_by_image_over_max_upload_bytes_returns_413(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _session = app_with_db
    _patch_reverse_search_settings(monkeypatch, max_upload_bytes=10)
    monkeypatch.setattr(
        "photofant.inference.image_embedder.resolve_image_embedder", lambda: _FakeEmbedder(),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/search/by-image", files={"file": ("upload.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "UPLOAD_TOO_LARGE"
