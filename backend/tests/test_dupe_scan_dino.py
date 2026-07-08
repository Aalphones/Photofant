"""P37 Phase 4 — duplicate detection moved from CLIP/SigLIP2 to DINOv2 (ADR-024).

Covers every place that used to read `asset.clip_embedding` for dupe/near-dupe
detection and now reads `asset.dino_embedding`: the post-embedding check, the
full/selection scan job, the person-scoped duplicate search, and the
training-set near-dupe stat/review. SigLIP2 must no longer be read by any of
these paths; `dupe_clip_*` settings stay present but inert.
"""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import (
    Asset,
    AssetInstance,
    Collection,
    CollectionItem,
    Person,
    ReviewItem,
)
from photofant.db.session import get_session
from photofant.jobs import dupe_scan_job
from photofant.jobs.embedding_job import _check_for_dupes
from photofant.jobs.queue import JobKind, JobState, JobStatus
from photofant.main import create_app
from photofant.settings import SETTINGS_DEFAULTS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _vec(*values: float) -> np.ndarray:
    return np.array(values, dtype=np.float32)


def _seed_asset(
    session: Session,
    *,
    content_hash: str,
    clip: np.ndarray | None = None,
    dino: np.ndarray | None = None,
    person_id: int = 1,
) -> Asset:
    asset = Asset(
        content_hash=content_hash,
        source="original",
        clip_embedding=clip.tobytes() if clip is not None else None,
        dino_embedding=dino.tobytes() if dino is not None else None,
    )
    session.add(asset)
    session.flush()
    session.add(AssetInstance(asset_id=asset.id, person_id=person_id, path=f"/tmp/{content_hash}.jpg"))
    session.commit()
    return asset


def _job_status(kind: JobKind) -> JobStatus:
    return JobStatus(id="test", kind=kind, label="test", state=JobState.RUNNING)


def _settings_dict(**overrides: Any) -> dict[str, Any]:
    merged = dict(SETTINGS_DEFAULTS)
    merged.update(overrides)
    return merged  # type: ignore[return-value]


# Near-identical DINOv2 pair (cosine ~0.99) vs. a clearly different third asset.
_DINO_NEAR_A = _vec(1.0, 0.0, 0.0, 0.0)
_DINO_NEAR_B = _vec(0.995, 0.0999, 0.0, 0.0)
_DINO_FAR = _vec(0.0, 1.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# dupe_scan_job — full/selection scan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dupe_scan_reads_dino_not_clip(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    # asset_a/b share a DINOv2 near-duplicate but have deliberately *different*
    # CLIP vectors — a CLIP-based scan would miss this pair, proving the scan
    # no longer reads clip_embedding.
    asset_a = _seed_asset(db_session, content_hash="a", clip=_vec(1, 0, 0, 0), dino=_DINO_NEAR_A)
    asset_b = _seed_asset(db_session, content_hash="b", clip=_vec(0, 0, 1, 0), dino=_DINO_NEAR_B)
    asset_c = _seed_asset(db_session, content_hash="c", dino=_DINO_FAR)

    monkeypatch.setattr(
        "photofant.settings.load_settings",
        lambda: _settings_dict(dupe_clip_enabled=True, dupe_dino_threshold=0.05),
    )
    monkeypatch.setattr(dupe_scan_job, "SessionLocal", lambda: db_session)
    # SessionLocal is a context manager in production; the test session already is one.
    monkeypatch.setattr(db_session, "close", lambda: None)

    status = _job_status(JobKind.DUPE_SCAN)
    await dupe_scan_job.run_dupe_scan_job(status, scope="full", asset_ids=None)

    pairs = db_session.execute(
        select(ReviewItem).where(ReviewItem.type == "dupe_candidate")
    ).scalars().all()
    found_pairs = {(item.asset_a_id, item.asset_b_id) for item in pairs}

    assert (asset_a.id, asset_b.id) == min((asset_a.id, asset_b.id), (asset_a.id, asset_b.id))
    assert (min(asset_a.id, asset_b.id), max(asset_a.id, asset_b.id)) in found_pairs
    assert not any(asset_c.id in pair for pair in found_pairs)


@pytest.mark.asyncio
async def test_dupe_scan_skips_when_disabled(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_asset(db_session, content_hash="a", dino=_DINO_NEAR_A)
    _seed_asset(db_session, content_hash="b", dino=_DINO_NEAR_B)

    monkeypatch.setattr(
        "photofant.settings.load_settings",
        lambda: _settings_dict(dupe_clip_enabled=False, dupe_dino_threshold=0.05),
    )
    monkeypatch.setattr(dupe_scan_job, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    status = _job_status(JobKind.DUPE_SCAN)
    await dupe_scan_job.run_dupe_scan_job(status, scope="full", asset_ids=None)

    pairs = db_session.execute(select(ReviewItem)).scalars().all()
    assert pairs == []


# ---------------------------------------------------------------------------
# embedding_job._check_for_dupes — post-embedding check
# ---------------------------------------------------------------------------


def test_check_for_dupes_uses_dino_search(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    asset_a = _seed_asset(db_session, content_hash="a", dino=_DINO_NEAR_A)
    asset_b = _seed_asset(db_session, content_hash="b", dino=_DINO_NEAR_B)

    monkeypatch.setattr(
        "photofant.settings.load_settings",
        lambda: _settings_dict(dupe_clip_enabled=True, dupe_dino_threshold=0.05, dupe_search_limit=20),
    )

    calls: list[tuple[np.ndarray, int]] = []

    def _fake_search_dino(session: Session, query: np.ndarray, limit: int) -> list[tuple[int, float]]:
        calls.append((query, limit))
        return [(asset_a.id, 0.99)]

    monkeypatch.setattr("photofant.jobs.embedding_job.search_dino", _fake_search_dino)

    _check_for_dupes(db_session, asset_b.id, _DINO_NEAR_B)

    assert len(calls) == 1  # search_dino was called with the DINOv2 vector, not a CLIP one
    item = db_session.execute(select(ReviewItem).where(ReviewItem.type == "dupe_candidate")).scalar_one()
    assert {item.asset_a_id, item.asset_b_id} == {asset_a.id, asset_b.id}


def test_check_for_dupes_noop_when_disabled(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    asset_a = _seed_asset(db_session, content_hash="a", dino=_DINO_NEAR_A)

    monkeypatch.setattr(
        "photofant.settings.load_settings", lambda: _settings_dict(dupe_clip_enabled=False),
    )

    def _boom(*args: Any, **kwargs: Any) -> list[tuple[int, float]]:
        raise AssertionError("search_dino must not be called when dupe detection is disabled")

    monkeypatch.setattr("photofant.jobs.embedding_job.search_dino", _boom)

    _check_for_dupes(db_session, asset_a.id, _DINO_NEAR_A)  # must return early, no crash


# ---------------------------------------------------------------------------
# api/duplicates.py — person-scoped duplicate search
# ---------------------------------------------------------------------------


@pytest.fixture
def app_with_db(db_session: Session) -> Generator[Any, None, None]:
    app = create_app()

    def _override() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_person_duplicates_uses_dino_embedding(
    app_with_db: Any, db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    person = Person(id=2, name="Alice", is_unknown=False)
    db_session.add(person)
    db_session.commit()

    # Different CLIP vectors, near-identical DINOv2 vectors — only a DINOv2-based
    # scan finds this pair.
    asset_a = _seed_asset(
        db_session, content_hash="a", clip=_vec(1, 0, 0, 0), dino=_DINO_NEAR_A, person_id=2,
    )
    asset_b = _seed_asset(
        db_session, content_hash="b", clip=_vec(0, 1, 0, 0), dino=_DINO_NEAR_B, person_id=2,
    )

    monkeypatch.setattr(
        "photofant.settings.load_settings",
        lambda: _settings_dict(dupe_dino_threshold=0.05),
    )

    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
        response = await client.post("/api/duplicates/search", json={"person_id": person.id})

    assert response.status_code == 200, response.text
    pairs = response.json()
    assert len(pairs) == 1
    assert {pairs[0]["asset_a_id"], pairs[0]["asset_b_id"]} == {asset_a.id, asset_b.id}


# ---------------------------------------------------------------------------
# collections — training-set near-dupe rate + review pairs
# ---------------------------------------------------------------------------


def test_training_near_dupe_rate_uses_dino(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from photofant.collections.stats import compute_training_set_stats

    collection = Collection(id=1, name="Training", kind="training_set")
    db_session.add(collection)
    db_session.commit()

    asset_a = _seed_asset(db_session, content_hash="a", clip=_vec(1, 0, 0, 0), dino=_DINO_NEAR_A)
    asset_b = _seed_asset(db_session, content_hash="b", clip=_vec(0, 1, 0, 0), dino=_DINO_NEAR_B)
    asset_c = _seed_asset(db_session, content_hash="c", dino=_DINO_FAR)
    for asset in (asset_a, asset_b, asset_c):
        db_session.add(CollectionItem(collection_id=collection.id, asset_id=asset.id))
    db_session.commit()

    monkeypatch.setattr(
        "photofant.settings.load_settings",
        lambda: _settings_dict(training_near_dupe_dino_threshold=0.05),
    )

    stats = compute_training_set_stats(db_session, collection.id)

    # a+b are DINOv2 near-dupes, c is not -> 2 of 3 assets have a partner.
    assert stats.near_dupe_rate == pytest.approx(2 / 3, abs=1e-4)


@pytest.mark.asyncio
async def test_collection_duplicates_endpoint_uses_dino(
    app_with_db: Any, db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = Collection(id=1, name="Training", kind="training_set")
    db_session.add(collection)
    db_session.commit()

    asset_a = _seed_asset(db_session, content_hash="a", clip=_vec(1, 0, 0, 0), dino=_DINO_NEAR_A)
    asset_b = _seed_asset(db_session, content_hash="b", clip=_vec(0, 1, 0, 0), dino=_DINO_NEAR_B)
    for asset in (asset_a, asset_b):
        db_session.add(CollectionItem(collection_id=collection.id, asset_id=asset.id))
    db_session.commit()

    monkeypatch.setattr(
        "photofant.settings.load_settings",
        lambda: _settings_dict(training_near_dupe_dino_threshold=0.05),
    )

    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
        response = await client.get(f"/api/collections/{collection.id}/duplicates")

    assert response.status_code == 200, response.text
    pairs = response.json()
    assert len(pairs) == 1
    assert {pairs[0]["asset_a_id"], pairs[0]["asset_b_id"]} == {asset_a.id, asset_b.id}
