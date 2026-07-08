"""KnowledgeService — Ownership-Regel, Markdown-first-CRUD, Lore-Stub (P22 Phase 3)."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from photofant.knowledge.schema import Entity, Owner, Relationship
from photofant.knowledge.service import (
    AmbiguousEntityError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    KnowledgeService,
    OwnershipConflictError,
)
from photofant.knowledge.validator import ValidationError
from photofant.knowledge.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()
    return instance


@pytest.fixture
def service(db_session: Session, vault: Vault) -> KnowledgeService:
    return KnowledgeService(db_session, vault)


def _actor(**overrides: object) -> Entity:
    defaults: dict[str, object] = {
        "id": "actors/robert-downey-jr",
        "type": "Actor",
        "title": "Robert Downey Jr.",
        "domain": "Movies",
        "aliases": ["RDJ"],
    }
    defaults.update(overrides)
    return Entity(**defaults)  # type: ignore[arg-type]


def _movie(**overrides: object) -> Entity:
    defaults: dict[str, object] = {
        "id": "movies/iron-man",
        "type": "Movie",
        "title": "Iron Man",
        "domain": "Movies",
    }
    defaults.update(overrides)
    return Entity(**defaults)  # type: ignore[arg-type]


def test_create_entity_writes_markdown_and_cache(service: KnowledgeService, vault: Vault) -> None:
    created = service.create_entity(_actor(), Owner.USER)

    assert created.owner is Owner.USER
    assert created.confidence == 1.0
    assert (vault.root / "actors" / "robert-downey-jr.md").exists()
    assert service.entities.get("actors/robert-downey-jr") is not None


def test_create_entity_forces_confidence_1_for_user_owner(service: KnowledgeService) -> None:
    created = service.create_entity(_actor(confidence=0.3), Owner.USER)
    assert created.confidence == 1.0


def test_create_entity_keeps_confidence_for_non_user_owner(service: KnowledgeService) -> None:
    created = service.create_entity(_actor(confidence=0.4), Owner.INFERRED)
    assert created.confidence == 0.4


def test_create_entity_rejects_duplicate_id(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    with pytest.raises(EntityAlreadyExistsError):
        service.create_entity(_actor(), Owner.USER)


def test_create_entity_rejects_unknown_type(service: KnowledgeService) -> None:
    with pytest.raises(ValidationError):
        service.create_entity(_actor(id="aliens/xenomorph", type="Alien"), Owner.USER)


def test_find_entity_by_id_and_alias(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)

    by_id = service.find_entity("actors/robert-downey-jr")
    by_alias = service.find_entity("RDJ")

    assert by_id is not None
    assert by_alias is not None
    assert by_id.id == by_alias.id == "actors/robert-downey-jr"


def test_find_entity_returns_none_when_missing(service: KnowledgeService) -> None:
    assert service.find_entity("actors/nobody") is None


def test_find_entity_ambiguous_alias_raises(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.create_entity(
        _actor(id="actors/robert-de-niro", title="Robert De Niro", aliases=["RDJ"]), Owner.USER
    )

    with pytest.raises(AmbiguousEntityError):
        service.find_entity("RDJ")


def test_update_entity_applies_patch_markdown_first(service: KnowledgeService, vault: Vault) -> None:
    service.create_entity(_actor(), Owner.USER)

    updated = service.update_entity(
        "actors/robert-downey-jr", {"status": "active", "aliases": ["RDJ", "Iron Man"]}, Owner.USER
    )

    assert updated.status == "active"
    assert updated.aliases == ["RDJ", "Iron Man"]
    on_disk = vault.load_entity(vault.root / "actors" / "robert-downey-jr.md")
    assert on_disk.status == "active"


def test_update_entity_rejects_immutable_fields(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    with pytest.raises(ValidationError):
        service.update_entity("actors/robert-downey-jr", {"domain": "Other"}, Owner.USER)


def test_update_entity_missing_raises_not_found(service: KnowledgeService) -> None:
    with pytest.raises(EntityNotFoundError):
        service.update_entity("actors/nobody", {"status": "active"}, Owner.USER)


def test_update_entity_rejects_lower_priority_owner(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    with pytest.raises(OwnershipConflictError):
        service.update_entity("actors/robert-downey-jr", {"status": "inferred-write"}, Owner.INFERRED)


def test_update_entity_allows_equal_or_higher_priority_owner(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.MANUAL)
    updated = service.update_entity("actors/robert-downey-jr", {"status": "confirmed"}, Owner.USER)
    assert updated.owner is Owner.USER
    assert updated.status == "confirmed"


def test_delete_entity_removes_file_and_cache(service: KnowledgeService, vault: Vault) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.delete_entity("actors/robert-downey-jr")

    assert not (vault.root / "actors" / "robert-downey-jr.md").exists()
    assert service.entities.get("actors/robert-downey-jr") is None


def test_delete_entity_missing_raises_not_found(service: KnowledgeService) -> None:
    with pytest.raises(EntityNotFoundError):
        service.delete_entity("actors/nobody")


def test_create_relationship_appends_and_dedups(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.create_entity(_movie(), Owner.USER)

    relationship = Relationship(type="plays", target="movies/iron-man")
    service.create_relationship("actors/robert-downey-jr", relationship, Owner.USER)
    updated = service.create_relationship("actors/robert-downey-jr", relationship, Owner.USER)

    assert updated.relationships == [relationship]


def test_create_relationship_rejects_unknown_type(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    with pytest.raises(ValidationError):
        service.create_relationship(
            "actors/robert-downey-jr", Relationship(type="not_a_real_type", target="movies/iron-man"), Owner.USER
        )


def test_remove_relationship_removes_entry(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.create_relationship(
        "actors/robert-downey-jr", Relationship(type="plays", target="movies/iron-man"), Owner.USER
    )

    updated = service.remove_relationship(
        "actors/robert-downey-jr", "plays", "movies/iron-man", Owner.USER
    )

    assert updated.relationships == []


def test_get_lore_returns_entity_and_outgoing_relationships(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.create_relationship(
        "actors/robert-downey-jr", Relationship(type="plays", target="movies/iron-man"), Owner.USER
    )

    lore = service.get_lore("actors/robert-downey-jr")

    assert lore.entity.id == "actors/robert-downey-jr"
    assert lore.relationships == [Relationship(type="plays", target="movies/iron-man")]


def test_search_entities_filters_by_type_and_domain(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.create_entity(_movie(), Owner.USER)

    results = service.search_entities("Iron Man", type="Movie", domain="Movies")

    assert [entity.id for entity in results] == ["movies/iron-man"]
