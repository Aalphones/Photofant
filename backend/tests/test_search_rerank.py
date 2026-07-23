"""P37 Phase 3 — DINOv2 two-stage re-ranking of image→image search.

Covers the rerank function in isolation and its wiring into the two image-query
paths (`like_asset_id` on /semantic, upload on /by-image), plus every degradation
branch: rerank disabled, text query, source without a DINOv2 vector, no DINOv2
model active. The SigLIP2 nearest-neighbour step (`vector_index.search`) is mocked
— the throwaway test DB has no sqlite-vec extension — while the DINOv2 vectors are
read from the real `asset.dino_embedding` BLOBs seeded into the DB.
"""
from __future__ import annotations

import io
from collections.abc import Generator
from typing import Any

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.api import search as search_api
from photofant.db import embeddings
from photofant.db.models import Asset, AssetInstance, Base, Person
from photofant.db.session import get_session
from photofant.main import create_app
from photofant.search.rerank import _rank_by_cosine, rerank_by_appearance
from photofant.settings import SETTINGS_DEFAULTS

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


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


def _vec(*values: float) -> np.ndarray:
    return np.array(values, dtype=np.float32)


def _seed_asset(
    session: Session,
    *,
    content_hash: str,
    clip: np.ndarray | None = None,
    dino: np.ndarray | None = None,
) -> Asset:
    asset = Asset(content_hash=content_hash, source="original")
    session.add(asset)
    session.flush()
    if clip is not None:
        embeddings.set_semantic(session, asset.id, clip)
    if dino is not None:
        embeddings.set_visual(session, asset.id, dino)
    session.add(AssetInstance(asset_id=asset.id, person_id=1, path=f"/tmp/{content_hash}.jpg"))
    session.commit()
    return asset


def _patch_settings(monkeypatch: pytest.MonkeyPatch, *, rerank_enabled: bool = True) -> None:
    rerank = {**SETTINGS_DEFAULTS["rerank"], "enabled": rerank_enabled}
    reverse_search = dict(SETTINGS_DEFAULTS["reverse_search"])
    monkeypatch.setattr(
        search_api, "load_settings", lambda: {"reverse_search": reverse_search, "rerank": rerank}
    )


def _patch_siglip_candidates(
    monkeypatch: pytest.MonkeyPatch, candidates: list[tuple[int, float]]
) -> None:
    monkeypatch.setattr(
        search_api.vector_index, "search", lambda session, embedding, limit: list(candidates)
    )


class _FakeTextEmbedder:
    """Satisfies TextEmbedder — used where the semantic_search role is resolved."""

    dim = 4

    def embed(self, image: np.ndarray) -> np.ndarray:
        return np.zeros(self.dim, dtype=np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        return np.zeros(self.dim, dtype=np.float32)


class _FakeDinoEmbedder:
    """Image-only embedder returning a fixed vector — the visual_rerank role."""

    dim = 4

    def __init__(self, vector: np.ndarray) -> None:
        self._vector = vector

    def embed(self, image: np.ndarray) -> np.ndarray:
        return self._vector


def _patch_resolver(
    monkeypatch: pytest.MonkeyPatch, *, semantic: Any = None, visual: Any = None
) -> None:
    def resolve(role: str = "semantic_search") -> Any:
        return semantic if role == "semantic_search" else visual

    monkeypatch.setattr("photofant.inference.image_embedder.resolve_image_embedder", resolve)


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color=(0, 128, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


# Query vector and three candidates whose DINOv2 order (C > B > A) is the reverse of
# a SigLIP2 order that lists A first — so a re-rank is unmistakable in assertions.
_QUERY_DINO = _vec(1.0, 0.0, 0.0, 0.0)
_DINO_A = _vec(0.0, 1.0, 0.0, 0.0)  # cosine 0.0 to query
_DINO_B = _vec(0.6, 0.8, 0.0, 0.0)  # cosine 0.6
_DINO_C = _vec(0.8, 0.6, 0.0, 0.0)  # cosine 0.8


# ---------------------------------------------------------------------------
# Pure ranking core
# ---------------------------------------------------------------------------


def test_rank_by_cosine_orders_by_similarity_descending() -> None:
    ranked = _rank_by_cosine(_QUERY_DINO, {10: _DINO_A, 20: _DINO_B, 30: _DINO_C}, top_k=3)

    assert [asset_id for asset_id, _ in ranked] == [30, 20, 10]
    assert ranked[0][1] == pytest.approx(0.8, abs=1e-6)


def test_rank_by_cosine_truncates_to_top_k() -> None:
    ranked = _rank_by_cosine(_QUERY_DINO, {10: _DINO_A, 20: _DINO_B, 30: _DINO_C}, top_k=2)

    assert [asset_id for asset_id, _ in ranked] == [30, 20]


def test_rank_by_cosine_empty_candidates_is_robust() -> None:
    assert _rank_by_cosine(_QUERY_DINO, {}, top_k=5) == []


def test_rerank_by_appearance_loads_vectors_and_orders(
    app_with_db: tuple[Any, Session],
) -> None:
    _app, session = app_with_db
    asset_a = _seed_asset(session, content_hash="a", dino=_DINO_A)
    asset_b = _seed_asset(session, content_hash="b", dino=_DINO_B)
    asset_c = _seed_asset(session, content_hash="c", dino=_DINO_C)
    without_vector = _seed_asset(session, content_hash="none")  # no dino_embedding

    ranked = rerank_by_appearance(
        session,
        _QUERY_DINO,
        [asset_a.id, asset_b.id, asset_c.id, without_vector.id],
        top_k=10,
    )

    # Only assets with a DINOv2 vector are ranked; the vectorless one drops out.
    assert [asset_id for asset_id, _ in ranked] == [asset_c.id, asset_b.id, asset_a.id]


# ---------------------------------------------------------------------------
# /semantic like_asset_id wiring + degradation
# ---------------------------------------------------------------------------


async def _post_like(app: Any, like_asset_id: int, limit: int = 10) -> list[int]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/search/semantic", json={"like_asset_id": like_asset_id, "limit": limit}
        )
    assert response.status_code == 200, response.text
    return [hit["asset_id"] for hit in response.json()["hits"]]


@pytest.mark.asyncio
async def test_like_asset_reranks_by_dino_appearance(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, session = app_with_db
    source = _seed_asset(session, content_hash="src", clip=_vec(1, 0, 0, 0), dino=_QUERY_DINO)
    asset_a = _seed_asset(session, content_hash="a", dino=_DINO_A)
    asset_b = _seed_asset(session, content_hash="b", dino=_DINO_B)
    asset_c = _seed_asset(session, content_hash="c", dino=_DINO_C)

    _patch_settings(monkeypatch, rerank_enabled=True)
    # SigLIP2 order is A, B, C — re-rank must flip it to C, B, A by appearance.
    _patch_siglip_candidates(monkeypatch, [(asset_a.id, 0.9), (asset_b.id, 0.8), (asset_c.id, 0.7)])

    assert await _post_like(app, source.id) == [asset_c.id, asset_b.id, asset_a.id]


@pytest.mark.asyncio
async def test_like_asset_no_rerank_when_disabled(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, session = app_with_db
    source = _seed_asset(session, content_hash="src", clip=_vec(1, 0, 0, 0), dino=_QUERY_DINO)
    asset_a = _seed_asset(session, content_hash="a", dino=_DINO_A)
    asset_b = _seed_asset(session, content_hash="b", dino=_DINO_B)
    asset_c = _seed_asset(session, content_hash="c", dino=_DINO_C)

    _patch_settings(monkeypatch, rerank_enabled=False)
    _patch_siglip_candidates(monkeypatch, [(asset_a.id, 0.9), (asset_b.id, 0.8), (asset_c.id, 0.7)])

    # rerank.enabled = false → plain SigLIP2 order preserved.
    assert await _post_like(app, source.id) == [asset_a.id, asset_b.id, asset_c.id]


@pytest.mark.asyncio
async def test_like_asset_no_rerank_when_source_has_no_dino_vector(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, session = app_with_db
    # Source has a SigLIP embedding but no DINOv2 vector — a valid state.
    source = _seed_asset(session, content_hash="src", clip=_vec(1, 0, 0, 0))
    asset_a = _seed_asset(session, content_hash="a", dino=_DINO_A)
    asset_b = _seed_asset(session, content_hash="b", dino=_DINO_B)
    asset_c = _seed_asset(session, content_hash="c", dino=_DINO_C)

    _patch_settings(monkeypatch, rerank_enabled=True)
    _patch_siglip_candidates(monkeypatch, [(asset_a.id, 0.9), (asset_b.id, 0.8), (asset_c.id, 0.7)])

    # No query DINOv2 vector → degrade to SigLIP2 order.
    assert await _post_like(app, source.id) == [asset_a.id, asset_b.id, asset_c.id]


@pytest.mark.asyncio
async def test_text_query_never_reranks(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, session = app_with_db
    asset_a = _seed_asset(session, content_hash="a", dino=_DINO_A)
    asset_b = _seed_asset(session, content_hash="b", dino=_DINO_B)
    asset_c = _seed_asset(session, content_hash="c", dino=_DINO_C)

    _patch_settings(monkeypatch, rerank_enabled=True)
    _patch_resolver(monkeypatch, semantic=_FakeTextEmbedder())
    _patch_siglip_candidates(monkeypatch, [(asset_a.id, 0.9), (asset_b.id, 0.8), (asset_c.id, 0.7)])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/search/semantic", json={"query": "roter sportwagen", "limit": 10}
        )

    assert response.status_code == 200, response.text
    # DINOv2 has no text encoder — the SigLIP2 order stands untouched.
    assert [hit["asset_id"] for hit in response.json()["hits"]] == [asset_a.id, asset_b.id, asset_c.id]


# ---------------------------------------------------------------------------
# /by-image upload wiring + degradation
# ---------------------------------------------------------------------------


async def _post_upload(app: Any) -> list[int]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/search/by-image", files={"file": ("upload.png", _png_bytes(), "image/png")}
        )
    assert response.status_code == 200, response.text
    return [hit["asset_id"] for hit in response.json()["hits"]]


@pytest.mark.asyncio
async def test_by_image_reranks_with_upload_dino_vector(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, session = app_with_db
    asset_a = _seed_asset(session, content_hash="a", dino=_DINO_A)
    asset_b = _seed_asset(session, content_hash="b", dino=_DINO_B)
    asset_c = _seed_asset(session, content_hash="c", dino=_DINO_C)

    _patch_settings(monkeypatch, rerank_enabled=True)
    _patch_resolver(
        monkeypatch, semantic=_FakeTextEmbedder(), visual=_FakeDinoEmbedder(_QUERY_DINO)
    )
    _patch_siglip_candidates(monkeypatch, [(asset_a.id, 0.9), (asset_b.id, 0.8), (asset_c.id, 0.7)])

    assert await _post_upload(app) == [asset_c.id, asset_b.id, asset_a.id]


@pytest.mark.asyncio
async def test_by_image_no_rerank_when_no_dino_model_active(
    app_with_db: tuple[Any, Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, session = app_with_db
    asset_a = _seed_asset(session, content_hash="a", dino=_DINO_A)
    asset_b = _seed_asset(session, content_hash="b", dino=_DINO_B)
    asset_c = _seed_asset(session, content_hash="c", dino=_DINO_C)

    _patch_settings(monkeypatch, rerank_enabled=True)
    # No visual_rerank model enabled → resolver returns None for that role.
    _patch_resolver(monkeypatch, semantic=_FakeTextEmbedder(), visual=None)
    _patch_siglip_candidates(monkeypatch, [(asset_a.id, 0.9), (asset_b.id, 0.8), (asset_c.id, 0.7)])

    # No DINOv2 model → degrade to SigLIP2 order.
    assert await _post_upload(app) == [asset_a.id, asset_b.id, asset_c.id]
