"""Phase 3 (P-Gesichter-Mehrfachauswahl, ADR-035) — Trainingsset-Stats + Export mit
Face-Items.

Face-Items zaehlen in `total`/`ar_buckets` mit (bbox-Maße statt echter Crop-Pixel-Maße),
bleiben aber außen vor bei `framing`/`quality_histogram`/`tag_frequencies`/`near_dupe_rate`
(README "Wichtige Funde" / "Scope-Schnitt"). Export erzeugt Bilddateien für Face-Items aus
`crop_path`, Caption ausschließlich aus `caption_override` (kein Foto-Fallback).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from photofant.collections.stats import DistItem, compute_training_set_stats
from photofant.db.models import Asset, AssetInstance, Collection, CollectionItem, Face
from photofant.jobs import export_job
from photofant.jobs.export_job import _collection_item_rows


def _seed_asset(
    session: Session,
    *,
    content_hash: str,
    framing: str | None = None,
    quality_score: float | None = None,
    width: int = 1024,
    height: int = 1024,
) -> Asset:
    asset = Asset(
        content_hash=content_hash,
        source="original",
        framing=framing,
        quality_score=quality_score,
        width=width,
        height=height,
    )
    session.add(asset)
    session.flush()
    session.add(AssetInstance(asset_id=asset.id, person_id=1, path=f"/tmp/{content_hash}.jpg"))
    session.commit()
    return asset


def _seed_face(session: Session, *, crop_path: str, bbox: dict[str, int] | None) -> Face:
    face = Face(asset_id=None, crop_path=crop_path, bbox=bbox)
    session.add(face)
    session.commit()
    return face


def test_stats_mixed_asset_and_face_items(db_session: Session) -> None:
    collection = Collection(id=1, name="Training", kind="training_set")
    db_session.add(collection)
    db_session.commit()

    asset = _seed_asset(db_session, content_hash="a", framing="portrait", quality_score=0.8)
    face = _seed_face(db_session, crop_path="/tmp/face.jpg", bbox={"x1": 0, "y1": 0, "x2": 512, "y2": 512})
    db_session.add(CollectionItem(collection_id=collection.id, asset_id=asset.id))
    db_session.add(CollectionItem(collection_id=collection.id, face_id=face.id))
    db_session.commit()

    stats = compute_training_set_stats(db_session, collection.id)

    assert stats.total == 2
    # Asset (1024x1024) und Face-bbox (512x512) landen beide im 1:1-Bucket bei je einer eigenen Basis.
    assert sum(item.count for item in stats.ar_buckets) == 2
    # Framing bleibt asset-only — nur der Asset-Eintrag zaehlt.
    assert stats.framing == [DistItem(value="portrait", count=1)]
    assert len(stats.quality_histogram) == 5
    assert sum(bucket.count for bucket in stats.quality_histogram) == 1
    # Nur ein Asset mit Embedding -> kein Near-Dupe-Partner moeglich.
    assert stats.near_dupe_rate == 0.0


def test_stats_face_without_bbox_skips_ar_bucket(db_session: Session) -> None:
    collection = Collection(id=1, name="Training", kind="training_set")
    db_session.add(collection)
    db_session.commit()

    face = _seed_face(db_session, crop_path="/tmp/face.jpg", bbox=None)
    db_session.add(CollectionItem(collection_id=collection.id, face_id=face.id))
    db_session.commit()

    stats = compute_training_set_stats(db_session, collection.id)

    assert stats.total == 1
    assert stats.ar_buckets == []
    assert stats.framing == []
    assert stats.tag_frequencies == []


def test_stats_asset_only_collection_unchanged(db_session: Session) -> None:
    """Regression: eine Collection ohne Face-Items liefert dieselben Werte wie vor Phase 3."""
    collection = Collection(id=1, name="Training", kind="training_set")
    db_session.add(collection)
    db_session.commit()

    asset = _seed_asset(db_session, content_hash="a", framing="portrait", quality_score=0.4)
    db_session.add(CollectionItem(collection_id=collection.id, asset_id=asset.id))
    db_session.commit()

    stats = compute_training_set_stats(db_session, collection.id)

    assert stats.total == 1
    assert len(stats.ar_buckets) == 1
    assert stats.framing[0].value == "portrait"


def test_export_rows_mixed_asset_and_face_items(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_collection_item_rows`` oeffnet seine eigene Session ueber ``SessionLocal`` (Job-Muster)
    — hier auf die Test-Session umgebogen, analog zu ``test_dupe_scan_dino.py``."""
    monkeypatch.setattr(export_job, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    collection = Collection(id=1, name="Training", kind="training_set")
    db_session.add(collection)
    db_session.commit()

    asset = _seed_asset(db_session, content_hash="a")
    db_session.add(CollectionItem(collection_id=collection.id, asset_id=asset.id, caption_override="Asset-Caption"))
    face_with_override = _seed_face(db_session, crop_path="/tmp/face1.jpg", bbox=None)
    face_without_override = _seed_face(db_session, crop_path="/tmp/face2.jpg", bbox=None)
    db_session.add(
        CollectionItem(collection_id=collection.id, face_id=face_with_override.id, caption_override="Face-Caption")
    )
    db_session.add(CollectionItem(collection_id=collection.id, face_id=face_without_override.id))
    db_session.commit()

    rows = _collection_item_rows(collection.id)

    assert len(rows) == 3
    by_path = {path: (caption, tags) for path, caption, tags in rows}
    assert by_path[Path("/tmp/a.jpg")] == ("Asset-Caption", [])
    assert by_path[Path("/tmp/face1.jpg")] == ("Face-Caption", [])
    # Kein caption_override + kein Foto-Fallback -> caption bleibt None (Sidecar wird leer, kein Absturz).
    assert by_path[Path("/tmp/face2.jpg")] == (None, [])
