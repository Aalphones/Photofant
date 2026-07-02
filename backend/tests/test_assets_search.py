"""q_mode=text search semantics after the fuzzy-match removal (ADR-015-Nachtrag).

Covers the three OR-branches of `SearchMode.TEXT` in `list_assets`: tag-name
substring match, person-name substring match, and caption match — both via
the FTS5 index (when migration 0028 ran) and via the ILIKE fallback (a
throwaway test DB has no FTS table, since `Base.metadata` doesn't know about
it — the index is created by raw SQL in the migration, mirroring how
`vector_index`'s vec0 table is excluded from `Base.metadata`).
"""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import Asset, AssetInstance, AssetTag, Base, Person, Tag
from photofant.db.session import get_session
from photofant.main import create_app


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


def _create_fts_table(session: Session) -> None:
    """Mirror migration 0028's FTS5 setup on a throwaway test DB (no triggers needed —
    tests insert rows directly into the FTS table alongside the asset row)."""
    session.execute(
        text(
            "CREATE VIRTUAL TABLE asset_caption_fts USING fts5("
            "caption, content='asset', content_rowid='id', "
            "tokenize='unicode61 remove_diacritics 2')"
        )
    )
    session.commit()


def _seed_asset(
    session: Session,
    *,
    content_hash: str,
    caption: str | None = None,
    person_id: int = 1,
) -> Asset:
    asset = Asset(content_hash=content_hash, source="original", caption=caption)
    session.add(asset)
    session.flush()
    instance = AssetInstance(asset_id=asset.id, person_id=person_id, path=f"/tmp/{content_hash}.jpg")
    session.add(instance)
    session.commit()
    return asset


async def _search_text(app: Any, query: str) -> list[int]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/assets", params={"q": query, "q_mode": "text"})
    assert response.status_code == 200
    return [item["id"] for item in response.json()["items"]]


@pytest.mark.asyncio
async def test_text_search_matches_tag_name_substring(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    asset = _seed_asset(session, content_hash="tag-match")
    tag = Tag(name="black_hair")
    session.add(tag)
    session.flush()
    session.add(AssetTag(asset_id=asset.id, tag_id=tag.id, kind="auto"))
    session.commit()

    ids = await _search_text(app, "hair")
    assert ids == [asset.id]


@pytest.mark.asyncio
async def test_text_search_matches_person_name_substring(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    person = Person(name="Sascha Müller", is_unknown=False)
    session.add(person)
    session.flush()
    asset = _seed_asset(session, content_hash="person-match", person_id=person.id)
    session.commit()

    ids = await _search_text(app, "sascha")
    assert ids == [asset.id]


@pytest.mark.asyncio
async def test_text_search_no_match_returns_empty(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    _seed_asset(session, content_hash="no-match", caption="a black cat on a red couch")
    session.commit()

    ids = await _search_text(app, "zzzzznonexistentqueryxyz")
    assert ids == []


@pytest.mark.asyncio
async def test_text_search_caption_falls_back_to_ilike_without_fts_index(
    app_with_db: tuple[Any, Session],
) -> None:
    """Test DB has no asset_caption_fts table (Base.metadata doesn't create it, mirroring
    vec_asset_embedding) — search_caption_asset_ids returns None, caller falls back to ILIKE."""
    app, session = app_with_db
    asset = _seed_asset(session, content_hash="caption-fallback", caption="a black cat on a red couch")
    session.commit()

    ids = await _search_text(app, "black")
    assert ids == [asset.id]


@pytest.mark.asyncio
async def test_text_search_caption_via_fts_prefix_match(app_with_db: tuple[Any, Session]) -> None:
    app, session = app_with_db
    _create_fts_table(session)
    asset = _seed_asset(session, content_hash="caption-fts", caption="a black cat on a red couch")
    session.execute(
        text("INSERT INTO asset_caption_fts(rowid, caption) VALUES (:rowid, :caption)"),
        {"rowid": asset.id, "caption": "a black cat on a red couch"},
    )
    session.commit()

    # Prefix match: "bla" should hit "black" via the trailing '*' in the sanitized query.
    ids = await _search_text(app, "bla")
    assert ids == [asset.id]


@pytest.mark.asyncio
async def test_text_search_fts_ignores_special_syntax_characters(
    app_with_db: tuple[Any, Session],
) -> None:
    """A query containing FTS5 syntax characters must not raise OperationalError."""
    app, session = app_with_db
    _create_fts_table(session)
    _seed_asset(session, content_hash="syntax-safe", caption="a black cat")
    session.commit()

    ids = await _search_text(app, '"black" OR cat*')
    assert ids == []
