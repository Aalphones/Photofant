"""KnowledgeService — Ownership-Regel, Markdown-first-CRUD, Lore-Stub (P22 Phase 3)."""
from __future__ import annotations

from datetime import UTC, datetime
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
from photofant.knowledge.tasks import TaskKind, TaskService
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


def test_updated_at_for_reflects_markdown_file_mtime(service: KnowledgeService) -> None:
    created = service.create_entity(_actor(), Owner.USER)

    updated_at = service.updated_at_for(created)

    assert updated_at is not None
    assert updated_at.tzinfo is not None
    assert updated_at <= datetime.now(UTC)


def test_updated_at_for_unresolvable_path_returns_none(service: KnowledgeService, vault: Vault) -> None:
    created = service.create_entity(_actor(), Owner.USER)
    (vault.root / "actors" / "robert-downey-jr.md").unlink()

    assert service.updated_at_for(created) is None


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


def test_create_entity_without_body_or_relationships_flags_incomplete_task(
    service: KnowledgeService, db_session: Session
) -> None:
    service.create_entity(_actor(), Owner.USER)

    tasks = TaskService(db_session).list_tasks()

    # P38 Phase 4: "Actor" hat definierte Merkmale (movies.yaml) — eine frisch angelegte,
    # leere Entity zieht zusätzlich zu INCOMPLETE_ENTITY auch MISSING_FIELD (kein Merkmal
    # gefüllt). LOW_COMPLETENESS bleibt aus, weil "kein Merkmal gefüllt" ≠ "kaum gefüllt".
    incomplete = [task for task in tasks if task.kind == TaskKind.INCOMPLETE_ENTITY.value]
    missing_field = [task for task in tasks if task.kind == TaskKind.MISSING_FIELD.value]
    assert len(tasks) == 2
    assert len(incomplete) == 1
    assert incomplete[0].context == {
        "entity_id": "actors/robert-downey-jr",
        "title": "Robert Downey Jr.",
        "type": "Actor",
    }
    assert len(missing_field) == 1
    assert missing_field[0].context["entity_id"] == "actors/robert-downey-jr"


def test_create_entity_with_body_does_not_flag_incomplete_task(
    service: KnowledgeService, db_session: Session
) -> None:
    service.create_entity(_actor(body="Bekannt aus Iron Man."), Owner.USER)

    tasks = TaskService(db_session).list_tasks()

    # Kein INCOMPLETE_ENTITY mehr (body gesetzt) — MISSING_FIELD bleibt, "Actor" hat
    # weiterhin drei ungefüllte Merkmale (P38 Phase 4).
    assert [task.kind for task in tasks] == [TaskKind.MISSING_FIELD.value]


def test_create_entity_with_relationship_does_not_flag_incomplete_task(
    service: KnowledgeService, db_session: Session
) -> None:
    service.create_entity(_movie(body="Marvel-Verfilmung von 2008."), Owner.USER)
    entity = _actor(relationships=[Relationship(type="plays", target="movies/iron-man")])

    service.create_entity(entity, Owner.USER)

    tasks = TaskService(db_session).list_tasks()

    # Kein INCOMPLETE_ENTITY (body bzw. Beziehung vorhanden) — beide Typen haben aber
    # definierte, ungefüllte Merkmale, deshalb je ein MISSING_FIELD (P38 Phase 4).
    assert {task.kind for task in tasks} == {TaskKind.MISSING_FIELD.value}
    assert {task.context["entity_id"] for task in tasks} == {
        "movies/iron-man",
        "actors/robert-downey-jr",
    }


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


def test_get_lore_resolves_relationship_targets_to_title_and_type(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.create_entity(_movie(), Owner.USER)
    service.create_relationship(
        "actors/robert-downey-jr", Relationship(type="plays", target="movies/iron-man"), Owner.USER
    )

    lore = service.get_lore("actors/robert-downey-jr")

    assert lore.entity is not None
    assert lore.entity.id == "actors/robert-downey-jr"
    assert len(lore.relationships) == 1
    resolved = lore.relationships[0]
    assert resolved.type == "plays"
    assert resolved.target.id == "movies/iron-man"
    assert resolved.target.title == "Iron Man"
    assert resolved.target.type == "Movie"


def test_get_lore_falls_back_to_raw_id_for_unknown_target(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.create_relationship(
        "actors/robert-downey-jr", Relationship(type="plays", target="movies/iron-man"), Owner.USER
    )

    lore = service.get_lore("actors/robert-downey-jr")

    resolved = lore.relationships[0]
    assert resolved.target.id == "movies/iron-man"
    assert resolved.target.title == "movies/iron-man"
    assert resolved.target.type == ""


def test_get_lore_splits_out_franchises(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.create_entity(
        Entity(id="franchises/mcu", type="Franchise", title="MCU", domain="Movies"), Owner.USER
    )
    service.create_relationship(
        "actors/robert-downey-jr", Relationship(type="member_of", target="franchises/mcu"), Owner.USER
    )

    lore = service.get_lore("actors/robert-downey-jr")

    assert [franchise.id for franchise in lore.franchises] == ["franchises/mcu"]
    assert len(lore.relationships) == 1  # Franchise bleibt zusätzlich in relationships[]


def test_get_lore_includes_sources_and_raw_media_links(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.update_entity(
        "actors/robert-downey-jr", {"sources": ["https://example.com"]}, Owner.USER
    )
    service.link_media("actors/robert-downey-jr", "person", 42, Owner.USER)

    lore = service.get_lore("actors/robert-downey-jr")

    assert lore.sources == ["https://example.com"]
    assert lore.related_media.persons == [42]


def test_get_lore_for_media_without_link_returns_empty_lore(service: KnowledgeService) -> None:
    lore = service.get_lore_for_media(person_id=42)

    assert lore.entity is None
    assert lore.relationships == []
    assert lore.franchises == []
    assert lore.sources == []


def test_get_lore_for_media_resolves_via_linked_entity(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.link_media("actors/robert-downey-jr", "person", 42, Owner.USER)

    lore = service.get_lore_for_media(person_id=42)

    assert lore.entity is not None
    assert lore.entity.id == "actors/robert-downey-jr"


def test_link_media_appends_and_dedups(service: KnowledgeService, vault: Vault) -> None:
    service.create_entity(_actor(), Owner.USER)

    service.link_media("actors/robert-downey-jr", "person", 42, Owner.USER)
    updated = service.link_media("actors/robert-downey-jr", "person", 42, Owner.USER)

    assert updated.media_links.persons == [42]
    on_disk = vault.load_entity(vault.root / "actors" / "robert-downey-jr.md")
    assert on_disk.media_links.persons == [42]


def test_link_media_missing_entity_raises_not_found(service: KnowledgeService) -> None:
    with pytest.raises(EntityNotFoundError):
        service.link_media("actors/nobody", "person", 42, Owner.USER)


def test_link_media_rejects_lower_priority_owner(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    with pytest.raises(OwnershipConflictError):
        service.link_media("actors/robert-downey-jr", "person", 42, Owner.INFERRED)


def test_unlink_media_removes_target(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.link_media("actors/robert-downey-jr", "person", 42, Owner.USER)

    updated = service.unlink_media("actors/robert-downey-jr", "person", 42, Owner.USER)

    assert updated.media_links.persons == []


def test_unlink_media_missing_target_is_a_noop(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    updated = service.unlink_media("actors/robert-downey-jr", "person", 999, Owner.USER)
    assert updated.media_links.persons == []


def test_linked_entity_ref_returns_cache_projection_without_body(service: KnowledgeService) -> None:
    service.create_entity(_actor(body="Langer Wikipedia-Text..."), Owner.USER)
    service.link_media("actors/robert-downey-jr", "person", 42, Owner.USER)

    ref = service.linked_entity_ref("person", 42)

    assert ref is not None
    assert ref.id == "actors/robert-downey-jr"
    assert ref.title == "Robert Downey Jr."
    assert ref.type == "Actor"


def test_linked_entity_ref_none_when_unlinked(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    assert service.linked_entity_ref("person", 42) is None


def test_linked_entity_refs_bulk(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.create_entity(_movie(), Owner.USER)
    service.link_media("actors/robert-downey-jr", "person", 1, Owner.USER)
    service.link_media("movies/iron-man", "person", 2, Owner.USER)

    refs = service.linked_entity_refs("person", [1, 2, 3])

    assert refs[1].id == "actors/robert-downey-jr"
    assert refs[2].id == "movies/iron-man"
    assert 3 not in refs


def test_search_entities_filters_by_type_and_domain(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)
    service.create_entity(_movie(), Owner.USER)

    results = service.search_entities("Iron Man", type="Movie", domain="Movies")

    assert [entity.id for entity in results] == ["movies/iron-man"]
