"""DELETE /api/review/dupes — clear the duplicate review queue for a fresh scan.

Only *unresolved* dupe-candidate pairs are dropped; pairs the user already
decided (e.g. "keep both" → dismiss) keep their tombstone so a re-scan won't
surface them again. Mirrors the full scan's pre-scan purge rule.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import Asset, ReviewItem
from photofant.db.session import get_session
from photofant.main import create_app


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _seed_asset(session: Session, content_hash: str) -> Asset:
    asset = Asset(content_hash=content_hash, source="original")
    session.add(asset)
    session.flush()
    return asset


def _seed_pair(
    session: Session,
    asset_a: Asset,
    asset_b: Asset,
    *,
    resolved: bool = False,
) -> ReviewItem:
    item = ReviewItem(
        type="dupe_candidate",
        asset_a_id=min(asset_a.id, asset_b.id),
        asset_b_id=max(asset_a.id, asset_b.id),
        clip_distance=0.02,
        created_at=_now(),
        resolved_at=_now() if resolved else None,
        resolution="dismiss" if resolved else None,
    )
    session.add(item)
    session.flush()
    return item


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
async def test_clear_drops_unresolved_keeps_decided(
    app_with_db: Any, db_session: Session,
) -> None:
    asset_a = _seed_asset(db_session, "a")
    asset_b = _seed_asset(db_session, "b")
    asset_c = _seed_asset(db_session, "c")
    asset_d = _seed_asset(db_session, "d")
    asset_e = _seed_asset(db_session, "e")
    asset_f = _seed_asset(db_session, "f")

    _seed_pair(db_session, asset_a, asset_b)                     # unresolved
    _seed_pair(db_session, asset_c, asset_d)                     # unresolved
    kept = _seed_pair(db_session, asset_e, asset_f, resolved=True)  # decided → must survive
    db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
        response = await client.delete("/api/review/dupes")

    assert response.status_code == 200, response.text
    assert response.json()["deleted"] == 2

    remaining = db_session.execute(select(ReviewItem)).scalars().all()
    assert [item.id for item in remaining] == [kept.id]


@pytest.mark.asyncio
async def test_clear_empty_queue_returns_zero(app_with_db: Any, db_session: Session) -> None:
    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
        response = await client.delete("/api/review/dupes")

    assert response.status_code == 200, response.text
    assert response.json()["deleted"] == 0
