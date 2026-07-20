"""Recommendation-Cache-Invalidierung bei Wissensgraph-Verknüpfungen (Phase 3 des Plans
``2026-07-20_recommendation-cache-invalidation``).

Testet nur, dass jede Aufrufer-Stelle (`link_person_entity`, `create_relationship`,
`update_entity`, `KnowledgePatchJob._run_patch`) vor ihrem Commit die passenden
`recommendation_cache`-Zeilen löscht — die Wissensgraph-Mechanik selbst ist bereits in
`test_knowledge_service.py`/`test_knowledge_api.py` abgedeckt.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.api import knowledge as knowledge_api
from photofant.api import persons as persons_api
from photofant.api.knowledge import CreateRelationshipRequest, MediaLinksDto, UpdateEntityRequest
from photofant.api.persons import LinkEntityRequest
from photofant.db.models import Asset, AssetInstance, Base, Person, Recommendation
from photofant.jobs.knowledge_patch_job import _run_patch
from photofant.knowledge.schema import Entity, MediaLinks, Owner
from photofant.knowledge.service import KnowledgeService
from photofant.knowledge.vault import Vault


def _add_asset(session: Session, asset_id: int) -> None:
    session.add(Asset(id=asset_id, content_hash=f"hash-{asset_id}"))


def _seed_recommendation(session: Session, source_id: int, target_id: int) -> None:
    session.add(
        Recommendation(
            source_asset_id=source_id,
            recommended_asset_id=target_id,
            score=0.5,
            reasons=[],
            computed_at=datetime.utcnow(),
        )
    )
    session.commit()


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()
    return instance


@pytest.mark.asyncio
async def test_link_person_entity_invalidates_all_person_assets(
    db_session: Session, vault: Vault
) -> None:
    db_session.add(Person(id=42, name="Jane Doe", is_unknown=False))
    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    _add_asset(db_session, 999)
    db_session.add(AssetInstance(asset_id=100, person_id=42, path="100.jpg"))
    db_session.add(AssetInstance(asset_id=200, person_id=42, path="200.jpg"))
    db_session.commit()

    _seed_recommendation(db_session, source_id=100, target_id=999)
    _seed_recommendation(db_session, source_id=999, target_id=200)

    KnowledgeService(db_session, vault).create_entity(
        Entity(id="actors/jane-doe", type="Actor", title="Jane Doe", domain="Movies"), Owner.USER
    )
    db_session.commit()

    await persons_api.link_person_entity(
        42, LinkEntityRequest(entity_id="actors/jane-doe"), db_session, vault
    )

    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []
    assert db_session.query(Recommendation).filter_by(source_asset_id=999).all() == []


@pytest.mark.asyncio
async def test_create_relationship_invalidates_linked_assets(
    db_session: Session, vault: Vault
) -> None:
    db_session.add(Person(id=42, name="Jane Doe", is_unknown=False))
    _add_asset(db_session, 100)
    db_session.add(AssetInstance(asset_id=100, person_id=42, path="100.jpg"))
    db_session.commit()

    _seed_recommendation(db_session, source_id=100, target_id=200)

    KnowledgeService(db_session, vault).create_entity(
        Entity(
            id="actors/jane-doe",
            type="Actor",
            title="Jane Doe",
            domain="Movies",
            media_links=MediaLinks(persons=[42]),
        ),
        Owner.USER,
    )
    db_session.commit()

    await knowledge_api.create_relationship(
        "actors/jane-doe",
        CreateRelationshipRequest(type="plays", target="movies/iron-man"),
        db_session,
        vault,
    )

    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []


@pytest.mark.asyncio
async def test_update_entity_media_links_removal_invalidates_old_and_new(
    db_session: Session, vault: Vault
) -> None:
    """Der in der README genannte Konfidenz-Check: ein generischer `media_links`-Patch
    kann eine Person entfernen und eine andere hinzufügen — beide Seiten müssen
    invalidiert werden, nicht nur die neu hinzugekommene."""
    db_session.add(Person(id=42, name="Person A", is_unknown=False))
    db_session.add(Person(id=43, name="Person B", is_unknown=False))
    _add_asset(db_session, 100)
    _add_asset(db_session, 200)
    db_session.add(AssetInstance(asset_id=100, person_id=42, path="100.jpg"))
    db_session.add(AssetInstance(asset_id=200, person_id=43, path="200.jpg"))
    db_session.commit()

    KnowledgeService(db_session, vault).create_entity(
        Entity(
            id="actors/jane-doe",
            type="Actor",
            title="Jane Doe",
            domain="Movies",
            media_links=MediaLinks(persons=[42]),
        ),
        Owner.USER,
    )
    db_session.commit()

    _seed_recommendation(db_session, source_id=100, target_id=999)
    _seed_recommendation(db_session, source_id=200, target_id=999)

    await knowledge_api.update_entity(
        "actors/jane-doe",
        UpdateEntityRequest(media_links=MediaLinksDto(persons=[43], assets=[])),
        db_session,
        vault,
    )

    assert db_session.query(Recommendation).filter_by(source_asset_id=100).all() == []
    assert db_session.query(Recommendation).filter_by(source_asset_id=200).all() == []


@pytest.mark.asyncio
async def test_update_entity_title_only_patch_is_noop(db_session: Session, vault: Vault) -> None:
    """Negativ-Test: ein Patch ohne `relationships`/`media_links` darf keine Cache-Zeile
    löschen — sonst wäre `needs_invalidation` versehentlich immer `True`."""
    db_session.add(Person(id=42, name="Jane Doe", is_unknown=False))
    _add_asset(db_session, 100)
    db_session.add(AssetInstance(asset_id=100, person_id=42, path="100.jpg"))
    db_session.commit()

    KnowledgeService(db_session, vault).create_entity(
        Entity(
            id="actors/jane-doe",
            type="Actor",
            title="Jane Doe",
            domain="Movies",
            media_links=MediaLinks(persons=[42]),
        ),
        Owner.USER,
    )
    db_session.commit()

    _seed_recommendation(db_session, source_id=100, target_id=999)

    await knowledge_api.update_entity(
        "actors/jane-doe", UpdateEntityRequest(title="Neuer Titel"), db_session, vault
    )

    assert len(db_session.query(Recommendation).filter_by(source_asset_id=100).all()) == 1


@pytest.fixture
def patch_job_session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'patch.sqlite'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr("photofant.jobs.knowledge_patch_job.SessionLocal", factory)
    return factory


@pytest.fixture
def patch_job_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()
    monkeypatch.setattr("photofant.jobs.knowledge_patch_job.open_vault", lambda: instance)
    return instance


def test_knowledge_patch_job_relationships_invalidates(
    patch_job_session_factory, patch_job_vault: Vault
) -> None:
    with patch_job_session_factory() as session:
        session.add(Person(id=42, name="Jane Doe", is_unknown=False))
        session.add(Asset(id=100, content_hash="hash-100"))
        session.add(AssetInstance(asset_id=100, person_id=42, path="100.jpg"))
        session.commit()

        KnowledgeService(session, patch_job_vault).create_entity(
            Entity(
                id="actors/jane-doe",
                type="Actor",
                title="Jane Doe",
                domain="Movies",
                media_links=MediaLinks(persons=[42]),
            ),
            Owner.USER,
        )
        session.commit()

        _seed_recommendation(session, source_id=100, target_id=999)

    _run_patch(
        "job-1",
        "actors/jane-doe",
        "relationships",
        [{"type": "plays", "target": "movies/iron-man"}],
        "Neue Rolle",
        Owner.USER,
    )

    with patch_job_session_factory() as session:
        assert session.query(Recommendation).filter_by(source_asset_id=100).all() == []
