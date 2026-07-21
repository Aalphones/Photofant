"""`total` in der Galerie-Antwort — schlanker Zähl-Pfad vs. volle Query.

`list_assets` zählt das Gesamtergebnis auf zwei Wegen: wenn kein Filter eine Spalte
aus `asset` braucht, über `_total_without_asset_join` (ohne den teuren Join), sonst
über die volle gefilterte Query. Welcher Weg genommen wird, entscheidet das Flag
`filters_touch_asset`.

Die Gefahr dabei: kommt ein neuer asset-seitiger Filter dazu und wird nicht in das
Flag aufgenommen, zählt die Galerie still zu viel — der Filter greift auf den Bildern,
aber nicht auf der Zahl darunter. Genau das prüfen die Tests hier, indem sie `total`
gegen die tatsächlich gelieferten Einträge halten: eine unabhängige Wahrheit, weil
Einträge und Zahl aus verschiedenen Code-Pfaden kommen.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

from photofant.db.models import (
    Asset,
    AssetClassification,
    AssetInstance,
    AssetTag,
    Base,
    ClassificationCategory,
    ClassificationLabel,
    Collection,
    CollectionItem,
    Face,
    Person,
    Tag,
    Version,
)
from photofant.db.session import get_session
from photofant.main import create_app


@pytest.fixture
def app_with_db(tmp_path) -> Generator[tuple[Any, Session], None, None]:  # type: ignore[no-untyped-def]
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        f"sqlite:///{tmp_path / 'assets.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add(Person(id=1, name="_unknown", is_unknown=True))
    session.add(Person(id=2, name="Alice", is_unknown=False))
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


def _seed_gallery(session: Session) -> None:
    """Three assets that differ in every filterable dimension, plus one Version-Pseudo-Eintrag.

    Every filter in the test matrix below must exclude at least one of them — a filter
    that matches everything would pass the test even if it were ignored entirely.
    """
    now = datetime.now(UTC).replace(tzinfo=None)

    session.add_all([
        Tag(id=1, name="sunset"),
        Tag(id=2, name="indoors"),
        ClassificationCategory(id=1, name="mood", mode="single", position=0, enabled=True),
    ])
    session.add(ClassificationLabel(id=1, category_id=1, name="calm", position=0))
    session.add(Collection(id=1, name="Favourites", kind="album"))
    session.flush()

    specs = [
        # content_hash, source,     framing,    quality, person, favourite, caption
        ("hash_a",      "original", "portrait", 0.9,     1,      True,      "a sunset over water"),
        ("hash_b",      "import",   "full",     0.2,     2,      False,     "an indoor scene"),
        ("hash_c",      "original", "portrait", 0.5,     1,      False,     "another sunset"),
    ]
    assets: dict[str, Asset] = {}
    instances: dict[str, AssetInstance] = {}
    for content_hash, source, framing, quality, person, favourite, caption in specs:
        asset = Asset(
            content_hash=content_hash, source=source, framing=framing,
            quality_score=quality, caption=caption, created_at=now,
        )
        session.add(asset)
        session.flush()
        instance = AssetInstance(
            asset_id=asset.id, person_id=person, favourite=favourite,
            path=f"/tmp/{content_hash}.jpg",
        )
        session.add(instance)
        session.flush()
        assets[content_hash] = asset
        instances[content_hash] = instance

    # Nur A: Tag "sunset", Collection-Mitglied, Klassifikation, ein Gesicht.
    session.add(AssetTag(asset_id=assets["hash_a"].id, tag_id=1, kind="auto", score=0.8))
    session.add(CollectionItem(collection_id=1, asset_id=assets["hash_a"].id, source="manual"))
    session.add(AssetClassification(
        asset_id=assets["hash_a"].id, label_id=1, category_id=1, confidence=0.9, source="clip",
    ))
    session.add(Face(asset_id=assets["hash_a"].id, person_id=1, crop_path="/tmp/face_a.jpg"))

    # Nur B: Tag "indoors" — sonst würde kein Tag-Filter je auf B greifen.
    session.add(AssetTag(asset_id=assets["hash_b"].id, tag_id=2, kind="auto", score=0.7))

    # Ein Editor-Dialog-Version-Eintrag an C: taucht als eigener Galerie-Eintrag auf
    # und muss in `total` mitgezählt werden — auf beiden Zähl-Pfaden.
    session.add(Version(
        instance_id=instances["hash_c"].id, face_id=None, type="edit",
        path="/tmp/hash_c_v1.jpg", is_current=True, created_at=now,
    ))
    session.commit()


# Jede Zeile: ein Filter, der mindestens einen Eintrag ausschließen muss.
# `favourite` und `person_id` nehmen den schlanken Pfad, alle anderen die volle Query.
FILTER_MATRIX: list[tuple[str, dict[str, Any]]] = [
    ("ungefiltert",           {}),
    ("favourite",             {"favourite": "true"}),
    ("person_id",             {"person_id": 1}),
    ("favourite+person",      {"favourite": "false", "person_id": 1}),
    ("source",                {"source": "original"}),
    ("framing",               {"framing": "portrait"}),
    ("quality_min",           {"quality_min": 0.6}),
    ("tags",                  {"tags": 1}),
    ("classification",        {"classification": 1}),
    ("collection_id",         {"collection_id": 1}),
    ("has_faces",             {"has_faces": "true"}),
    ("has_faces=false",       {"has_faces": "false"}),
    ("q (tags)",              {"q": "sunset"}),
    ("q (caption)",           {"q": "indoor", "q_mode": "caption"}),
    ("similar_ids",           {"similar_ids": 1}),
    ("source+person",         {"source": "original", "person_id": 1}),
]


@pytest.mark.anyio
@pytest.mark.parametrize(("label", "params"), FILTER_MATRIX, ids=[row[0] for row in FILTER_MATRIX])
async def test_total_matches_full_count_for_every_filter(
    app_with_db: tuple[Any, Session], label: str, params: dict[str, Any],
) -> None:
    """`total` muss zu den gelieferten Einträgen passen — egal welcher Zähl-Pfad greift.

    Ein asset-seitiger Filter, der in `filters_touch_asset` fehlt, fällt hier auf:
    die Einträge sind dann korrekt gefiltert, `total` aber ungefiltert und zu groß.
    """
    app, session = app_with_db
    _seed_gallery(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/assets", params={"page": 1, "page_size": 200, **params})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == len(body["items"]), (
        f"Filter '{label}': total={body['total']}, geliefert={len(body['items'])} — "
        f"greift der Filter im Zähl-Pfad nicht?"
    )


@pytest.mark.anyio
async def test_unfiltered_total_counts_versions_as_own_entries(
    app_with_db: tuple[Any, Session],
) -> None:
    """Der schlanke Pfad darf den Version-Pseudo-Eintrag nicht unterschlagen.

    Die Seed-Daten haben 3 Assets + 1 Editor-Version = 4 Galerie-Einträge; würde
    `_total_without_asset_join` nur Instanzen zählen, stünde hier 3.
    """
    app, session = app_with_db
    _seed_gallery(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/assets", params={"page": 1, "page_size": 200})

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 4


@pytest.mark.anyio
async def test_soft_deleted_instances_are_excluded_from_total(
    app_with_db: tuple[Any, Session],
) -> None:
    """Soft-Delete muss auf dem schlanken Pfad genauso greifen wie auf dem vollen."""
    app, session = app_with_db
    _seed_gallery(session)

    instance = session.query(AssetInstance).join(Asset).filter(Asset.content_hash == "hash_b").one()
    instance.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/assets", params={"page": 1, "page_size": 200})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    assert body["total"] == len(body["items"])
