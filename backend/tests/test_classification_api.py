"""Classification API — CRUD, explicit cascade-delete, and the OR/AND asset filter.

The explicit cascade-delete tests matter: SQLite runs without
`PRAGMA foreign_keys=ON` (project-wide, see P18 FINDINGS.md), so the declared
`ON DELETE CASCADE` on classification_label/asset_classification never fires —
the API has to clean up dependent rows itself.
"""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import (
    Asset,
    AssetClassification,
    AssetInstance,
    Base,
    ClassificationCategory,
    ClassificationLabel,
    Person,
)
from photofant.db.session import get_session
from photofant.main import create_app


@pytest.fixture
def app_with_db(tmp_path) -> Generator[tuple[Any, Session], None, None]:  # type: ignore[no-untyped-def]
    engine = create_engine(
        f"sqlite:///{tmp_path / 'classification.sqlite'}",
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


def _seed_category(session: Session, *, name: str, mode: str, position: int = 0) -> ClassificationCategory:
    category = ClassificationCategory(name=name, mode=mode, position=position)
    session.add(category)
    session.flush()
    return category


def _seed_label(
    session: Session, category: ClassificationCategory, *, name: str, position: int = 0,
) -> ClassificationLabel:
    label = ClassificationLabel(category_id=category.id, name=name, position=position)
    session.add(label)
    session.flush()
    return label


def _classify(session: Session, asset: Asset, label: ClassificationLabel, *, confidence: float = 0.9) -> None:
    session.add(AssetClassification(
        asset_id=asset.id, label_id=label.id, category_id=label.category_id,
        confidence=confidence, source="fused",
    ))


# ── CRUD ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_category_and_label_nested_in_list(app_with_db: tuple[Any, Session]) -> None:
    app, _ = app_with_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        category_response = await client.post(
            "/api/classification/categories", json={"name": "Medium", "mode": "single"},
        )
        assert category_response.status_code == 201
        category_id = category_response.json()["id"]

        label_response = await client.post(
            f"/api/classification/categories/{category_id}/labels", json={"name": "Foto"},
        )
        assert label_response.status_code == 201

        listed = await client.get("/api/classification/categories")

    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["name"] == "Medium"
    assert body[0]["mode"] == "single"
    assert [label["name"] for label in body[0]["labels"]] == ["Foto"]


@pytest.mark.asyncio
async def test_create_category_rejects_invalid_mode(app_with_db: tuple[Any, Session]) -> None:
    app, _ = app_with_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/classification/categories", json={"name": "Kaputt", "mode": "bogus"},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_category_updates_enabled_and_min_confidence(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    category = _seed_category(session, name="Stil", mode="multi")
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/classification/categories/{category.id}",
            json={"enabled": False, "min_confidence": 0.6},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["min_confidence"] == 0.6


@pytest.mark.asyncio
async def test_delete_category_cascades_labels_and_asset_classification(
    app_with_db: tuple[Any, Session],
) -> None:
    """Regression: without PRAGMA foreign_keys=ON, declared CASCADE never fires —
    the endpoint must delete dependent rows itself."""
    app, session = app_with_db
    category = _seed_category(session, name="Medium", mode="single")
    label = _seed_label(session, category, name="Foto")
    asset = _seed_asset(session, content_hash="a1")
    _classify(session, asset, label)
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/api/classification/categories/{category.id}")

    assert response.status_code == 204
    assert session.query(ClassificationCategory).count() == 0
    assert session.query(ClassificationLabel).count() == 0
    assert session.query(AssetClassification).count() == 0


@pytest.mark.asyncio
async def test_delete_label_cascades_asset_classification(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    category = _seed_category(session, name="Medium", mode="single")
    label = _seed_label(session, category, name="Foto")
    asset = _seed_asset(session, content_hash="a1")
    _classify(session, asset, label)
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/api/classification/labels/{label.id}")

    assert response.status_code == 204
    assert session.query(ClassificationLabel).count() == 0
    assert session.query(AssetClassification).count() == 0
    # Category itself survives — only the label + its assignments are gone.
    assert session.query(ClassificationCategory).count() == 1


@pytest.mark.asyncio
async def test_create_label_rejects_duplicate_name_in_category(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    category = _seed_category(session, name="Medium", mode="single")
    _seed_label(session, category, name="Foto")
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/classification/categories/{category.id}/labels", json={"name": "Foto"},
        )
    assert response.status_code == 409


# ── Filter: OR within a category, AND across categories ───────────────────────


@pytest.mark.asyncio
async def test_asset_filter_ors_within_category_ands_across_categories(
    app_with_db: tuple[Any, Session],
) -> None:
    app, session = app_with_db
    medium = _seed_category(session, name="Medium", mode="single")
    foto = _seed_label(session, medium, name="Foto", position=0)
    illustration = _seed_label(session, medium, name="Illustration", position=1)

    stil = _seed_category(session, name="Stil", mode="multi", position=1)
    anime = _seed_label(session, stil, name="Anime", position=0)
    realistisch = _seed_label(session, stil, name="Realistisch", position=1)

    asset_foto_anime = _seed_asset(session, content_hash="foto-anime")
    _classify(session, asset_foto_anime, foto)
    _classify(session, asset_foto_anime, anime)

    asset_illu_anime = _seed_asset(session, content_hash="illu-anime")
    _classify(session, asset_illu_anime, illustration)
    _classify(session, asset_illu_anime, anime)

    asset_foto_realistisch = _seed_asset(session, content_hash="foto-realistisch")
    _classify(session, asset_foto_realistisch, foto)
    _classify(session, asset_foto_realistisch, realistisch)
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/assets",
            params=[("classification", foto.id), ("classification", illustration.id), ("classification", anime.id)],
        )

    assert response.status_code == 200
    body = response.json()
    returned_ids = {item["id"] for item in body["items"]}
    assert returned_ids == {asset_foto_anime.id, asset_illu_anime.id}

    classification_facets = {facet["category_id"]: facet for facet in body["facets"]["classifications"]}
    assert classification_facets[medium.id]["items"]
    assert classification_facets[stil.id]["items"]


@pytest.mark.asyncio
async def test_asset_detail_lists_classifications_sorted_by_confidence(
    app_with_db: tuple[Any, Session],
) -> None:
    app, session = app_with_db
    medium = _seed_category(session, name="Medium", mode="single")
    foto = _seed_label(session, medium, name="Foto")
    stil = _seed_category(session, name="Stil", mode="multi", position=1)
    anime = _seed_label(session, stil, name="Anime")

    asset = _seed_asset(session, content_hash="detail-asset")
    _classify(session, asset, foto, confidence=0.4)
    _classify(session, asset, anime, confidence=0.9)
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/assets/{asset.id}")

    assert response.status_code == 200
    classifications = response.json()["classifications"]
    assert [entry["label_name"] for entry in classifications] == ["Anime", "Foto"]


@pytest.mark.asyncio
async def test_text_search_matches_classification_label_name(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    medium = _seed_category(session, name="Medium", mode="single")
    foto = _seed_label(session, medium, name="Foto")
    asset = _seed_asset(session, content_hash="label-search")
    _classify(session, asset, foto)
    session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/assets", params={"q": "foto", "q_mode": "text"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [asset.id]
