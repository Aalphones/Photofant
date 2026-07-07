"""Table-driven tests for the classification fusion engine (P18 Phase 2).

Covers the four scenarios named in the phase's acceptance criteria: single-mode
argmax, multi-mode threshold, WD14-signal-missing fallback to clip-only, and
CLIP-inactive fallback to WD14-only. CLIP scoring itself (`score_labels_clip`)
is monkeypatched throughout — it needs a real ONNX model, out of scope here —
except in the end-to-end WD14 test, which exercises the real
`score_label_wd14` + `_stored_tag_scores` path.
"""
from __future__ import annotations

from collections.abc import Generator

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.classification import engine
from photofant.db.models import (
    Asset,
    AssetTag,
    Base,
    ClassificationCategory,
    ClassificationLabel,
    Tag,
)

_DEFAULT_CLASSIFICATION_SETTINGS = {
    "clip_weight": 0.5,
    "wd14_weight": 0.5,
    "min_confidence": 0.3,
    "multi_min_confidence": 0.45,
    "clip_prompt_template": "a photo of {label}",
}


@pytest.fixture
def db_session(tmp_path) -> Generator[Session, None, None]:
    sqlite_engine = create_engine(
        f"sqlite:///{tmp_path / 'test.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(sqlite_engine)
    factory = sessionmaker(bind=sqlite_engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        sqlite_engine.dispose()


def _make_asset(session: Session, *, with_embedding: bool = True) -> Asset:
    asset = Asset(
        content_hash="hash-1",
        clip_embedding=np.zeros(768, dtype=np.float32).tobytes() if with_embedding else None,
    )
    session.add(asset)
    session.commit()
    return asset


def _make_category(
    session: Session,
    *,
    mode: str,
    labels: list[tuple[str, list[str] | None]],
    min_confidence: float | None = None,
) -> ClassificationCategory:
    category = ClassificationCategory(
        name=f"cat-{mode}-{len(labels)}", mode=mode, position=0, min_confidence=min_confidence,
    )
    session.add(category)
    session.flush()
    for position, (name, wd14_tags) in enumerate(labels):
        session.add(ClassificationLabel(
            category_id=category.id, name=name, position=position, wd14_tags=wd14_tags,
        ))
    session.commit()
    return category


def _patch_settings(monkeypatch: pytest.MonkeyPatch, **overrides: float | str) -> None:
    settings = {**_DEFAULT_CLASSIFICATION_SETTINGS, **overrides}
    monkeypatch.setattr(engine, "load_settings", lambda: {"classification": settings})


def test_single_category_argmax_wins_above_threshold(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Single-mode category picks the highest-fused label once it clears min_confidence."""
    _patch_settings(monkeypatch)
    monkeypatch.setattr(engine, "resolve_image_embedder", lambda: object())
    monkeypatch.setattr(engine, "score_labels_clip", lambda image_embedding, prompts: [0.2, 0.7, 0.1])
    monkeypatch.setattr(engine, "score_label_wd14", lambda wd14_tags, tag_scores: None)

    asset = _make_asset(db_session)
    category = _make_category(db_session, mode="single", labels=[("A", None), ("B", None), ("C", None)])

    results = engine.classify_asset(db_session, asset.id)

    assert len(results) == 1
    assert results[0].category_id == category.id
    assert results[0].confidence == pytest.approx(0.7)
    assert results[0].source == "clip"


def test_single_category_below_threshold_yields_no_result(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(monkeypatch, min_confidence=0.8)
    monkeypatch.setattr(engine, "resolve_image_embedder", lambda: object())
    monkeypatch.setattr(engine, "score_labels_clip", lambda image_embedding, prompts: [0.2, 0.7, 0.1])
    monkeypatch.setattr(engine, "score_label_wd14", lambda wd14_tags, tag_scores: None)

    asset = _make_asset(db_session)
    _make_category(db_session, mode="single", labels=[("A", None), ("B", None), ("C", None)])

    assert engine.classify_asset(db_session, asset.id) == []


def test_multi_category_selects_all_labels_above_threshold(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(monkeypatch)  # multi_min_confidence = 0.45
    monkeypatch.setattr(engine, "resolve_image_embedder", lambda: object())
    monkeypatch.setattr(engine, "score_labels_clip", lambda image_embedding, prompts: [0.5, 0.3, 0.9])
    monkeypatch.setattr(engine, "score_label_wd14", lambda wd14_tags, tag_scores: None)

    asset = _make_asset(db_session)
    category = _make_category(db_session, mode="multi", labels=[("A", None), ("B", None), ("C", None)])

    results = engine.classify_asset(db_session, asset.id)

    assert len(results) == 2  # 0.5 and 0.9 clear 0.45; 0.3 does not
    assert all(result.category_id == category.id for result in results)


def test_missing_wd14_tag_falls_back_to_clip_only(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Label has wd14_tags configured but no matching stored score — clip carries it alone."""
    _patch_settings(monkeypatch)
    monkeypatch.setattr(engine, "resolve_image_embedder", lambda: object())
    monkeypatch.setattr(engine, "score_labels_clip", lambda image_embedding, prompts: [0.6])
    monkeypatch.setattr(engine, "score_label_wd14", lambda wd14_tags, tag_scores: None)

    asset = _make_asset(db_session)
    _make_category(db_session, mode="single", labels=[("Anime", ["anime"])])

    results = engine.classify_asset(db_session, asset.id)

    assert len(results) == 1
    assert results[0].source == "clip"
    assert results[0].confidence == pytest.approx(0.6)


def test_wd14_signal_present_produces_fused_score(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(monkeypatch)
    monkeypatch.setattr(engine, "resolve_image_embedder", lambda: object())
    monkeypatch.setattr(engine, "score_labels_clip", lambda image_embedding, prompts: [0.6])
    monkeypatch.setattr(engine, "score_label_wd14", lambda wd14_tags, tag_scores: 0.8)

    asset = _make_asset(db_session)
    _make_category(db_session, mode="single", labels=[("Anime", ["anime"])])

    results = engine.classify_asset(db_session, asset.id)

    assert len(results) == 1
    assert results[0].source == "fused"
    assert results[0].confidence == pytest.approx(0.5 * 0.6 + 0.5 * 0.8)


def test_clip_inactive_falls_back_to_wd14_only(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_image_embedder() -> None: no crash, clip scoring is skipped entirely."""
    _patch_settings(monkeypatch)
    monkeypatch.setattr(engine, "resolve_image_embedder", lambda: None)
    monkeypatch.setattr(
        engine, "score_labels_clip",
        lambda image_embedding, prompts: pytest.fail("must not be called when CLIP is inactive"),
    )
    monkeypatch.setattr(
        engine, "score_label_wd14",
        lambda wd14_tags, tag_scores: 0.9 if wd14_tags == ["anime"] else None,
    )

    asset = _make_asset(db_session, with_embedding=True)
    _make_category(db_session, mode="single", labels=[("Anime", ["anime"]), ("Foto", None)])

    results = engine.classify_asset(db_session, asset.id)

    assert len(results) == 1
    assert results[0].source == "wd14"
    assert results[0].confidence == pytest.approx(0.9)


def test_no_stored_embedding_falls_back_to_wd14_only(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """asset.clip_embedding is None (e.g. auto_embed was off) — same fallback as CLIP-inactive."""
    _patch_settings(monkeypatch)
    monkeypatch.setattr(engine, "resolve_image_embedder", lambda: object())
    monkeypatch.setattr(
        engine, "score_labels_clip",
        lambda image_embedding, prompts: pytest.fail("must not be called without a stored embedding"),
    )
    monkeypatch.setattr(
        engine, "score_label_wd14",
        lambda wd14_tags, tag_scores: 0.5 if wd14_tags == ["cat"] else None,
    )

    asset = _make_asset(db_session, with_embedding=False)
    _make_category(db_session, mode="single", labels=[("Cat", ["cat"])])

    results = engine.classify_asset(db_session, asset.id)

    assert len(results) == 1
    assert results[0].source == "wd14"


def test_per_category_min_confidence_overrides_global_default(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(monkeypatch, min_confidence=0.3)
    monkeypatch.setattr(engine, "resolve_image_embedder", lambda: object())
    monkeypatch.setattr(engine, "score_labels_clip", lambda image_embedding, prompts: [0.4])
    monkeypatch.setattr(engine, "score_label_wd14", lambda wd14_tags, tag_scores: None)

    asset = _make_asset(db_session)
    _make_category(db_session, mode="single", labels=[("A", None)], min_confidence=0.9)

    # 0.4 clears the global default (0.3) but not the category override (0.9).
    assert engine.classify_asset(db_session, asset.id) == []


def test_end_to_end_uses_real_stored_wd14_score(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No mocking of score_label_wd14 — exercises the real DB tag-score lookup."""
    _patch_settings(monkeypatch)
    monkeypatch.setattr(engine, "resolve_image_embedder", lambda: None)

    asset = _make_asset(db_session)
    tag = Tag(name="cat")
    db_session.add(tag)
    db_session.flush()
    db_session.add(AssetTag(asset_id=asset.id, tag_id=tag.id, score=0.85))
    db_session.commit()

    _make_category(db_session, mode="single", labels=[("Cat", ["cat"])])

    results = engine.classify_asset(db_session, asset.id)

    assert len(results) == 1
    assert results[0].source == "wd14"
    assert results[0].confidence == pytest.approx(0.85)
