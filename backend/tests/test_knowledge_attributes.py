"""Merkmale mit eigenem Owner + Vollständigkeit (P38 Phase 2).

Deckt die drei Stellen ab, an denen die neue Struktur brechen könnte: der
Frontmatter-Round-Trip (Sonderzeichen, fehlender Block), die Validierung gegen die
Domänen-Felddefinitionen und der Schreibweg ``set_attributes``, dessen ganzer Zweck
es ist, ein einzelnes ``user``-Merkmal vor einem ``web``-Lauf zu schützen.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from photofant.knowledge.domains import load_domain
from photofant.knowledge.parser import parse_entity, serialize_entity
from photofant.knowledge.schema import Attribute, Entity, Owner
from photofant.knowledge.service import KnowledgeService
from photofant.knowledge.validator import ValidationError, validate_entity
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
    }
    defaults.update(overrides)
    return Entity(**defaults)  # type: ignore[arg-type]


def test_round_trip_survives_umlauts_colons_and_empty_values() -> None:
    entity = _actor(
        attributes={
            "geburtsort": Attribute(value="New York: Manhattan", owner=Owner.WEB, confidence=0.8),
            "taetigkeit": Attribute(value="Schauspieler, Ärztin-Rollen", owner=Owner.USER),
            "geburtstag": Attribute(value="", owner=Owner.INFERRED),
        }
    )

    text = serialize_entity(entity)
    parsed = parse_entity(text)

    assert parsed.attributes == entity.attributes
    # Zweite Runde muss byte-gleich sein, sonst wächst die Datei bei jedem Speichern.
    assert serialize_entity(parsed) == text


def test_file_without_attributes_block_loads_with_empty_mapping() -> None:
    text = """---
id: actors/jane-doe
type: Actor
title: Jane Doe
domain: Movies
owner: user
confidence: 1.0
---

Alte Datei aus der Zeit vor den Merkmalen.
"""
    assert parse_entity(text).attributes == {}


def test_undefined_attribute_is_rejected_with_readable_message(vault: Vault) -> None:
    domain = load_domain(vault.domain_path("Movies"))
    entity = _actor(attributes={"lieblingsfarbe": Attribute(value="blau")})

    errors = validate_entity(entity, domain)

    assert "Merkmal 'lieblingsfarbe' ist für Typ 'Actor' nicht definiert" in errors


def test_set_attributes_does_not_overwrite_user_value_and_says_why(
    service: KnowledgeService,
) -> None:
    service.create_entity(
        _actor(attributes={"geburtsort": Attribute(value="New York", owner=Owner.USER)}),
        Owner.USER,
    )

    entity, written, skipped = service.set_attributes(
        "actors/robert-downey-jr",
        {"geburtsort": Attribute(value="Los Angeles", owner=Owner.WEB)},
        Owner.WEB,
    )

    assert entity.attributes["geburtsort"].value == "New York"
    assert entity.attributes["geburtsort"].owner is Owner.USER
    assert written == []
    assert skipped == ["'Geburtsort' bleibt unverändert — der Wert stammt von dir"]


def test_set_attributes_leaves_entity_owner_untouched(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)

    entity, written, _skipped = service.set_attributes(
        "actors/robert-downey-jr",
        {"geburtstag": Attribute(value="1965-04-04", owner=Owner.WEB, confidence=0.9)},
        Owner.WEB,
    )

    assert entity.owner is Owner.USER
    assert written == ["geburtstag"]
    assert entity.attributes["geburtstag"].owner is Owner.WEB


def test_set_attributes_removes_key_on_empty_value(service: KnowledgeService) -> None:
    service.create_entity(
        _actor(attributes={"geburtstag": Attribute(value="1965-04-04", owner=Owner.WEB)}),
        Owner.USER,
    )

    entity, written, _skipped = service.set_attributes(
        "actors/robert-downey-jr", {"geburtstag": Attribute(value="  ", owner=Owner.WEB)}, Owner.WEB
    )

    assert "geburtstag" not in entity.attributes
    assert written == ["geburtstag"]


def test_set_attributes_rejects_undefined_key_without_writing(service: KnowledgeService) -> None:
    service.create_entity(_actor(), Owner.USER)

    with pytest.raises(ValidationError):
        service.set_attributes(
            "actors/robert-downey-jr", {"lieblingsfarbe": Attribute(value="blau")}, Owner.WEB
        )

    assert service.find_entity("actors/robert-downey-jr").attributes == {}  # type: ignore[union-attr]


def test_completeness_counts_filled_against_defined(service: KnowledgeService, vault: Vault) -> None:
    domain = load_domain(vault.domain_path("Movies"))
    # Actor hat drei definierte Merkmale; zwei davon gefüllt, eines leer.
    entity = _actor(
        attributes={
            "geburtstag": Attribute(value="1965-04-04"),
            "geburtsort": Attribute(value="New York"),
            "taetigkeit": Attribute(value=""),
        }
    )

    assert service.completeness_for(entity, domain) == pytest.approx(2 / 3)


def test_completeness_is_zero_for_type_without_defined_fields(
    service: KnowledgeService, vault: Vault
) -> None:
    domain = load_domain(vault.domain_path("Movies"))
    series = Entity(id="series/loki", type="Series", title="Loki", domain="Movies")

    assert service.completeness_for(series, domain) == 0.0


def test_linked_entity_ref_carries_completeness_from_cache(service: KnowledgeService) -> None:
    service.create_entity(
        _actor(attributes={"geburtstag": Attribute(value="1965-04-04", owner=Owner.WEB)}),
        Owner.USER,
    )
    service.link_media("actors/robert-downey-jr", "person", 42, Owner.USER)

    ref = service.linked_entity_ref("person", 42)

    assert ref is not None
    assert ref.completeness == pytest.approx(1 / 3)
