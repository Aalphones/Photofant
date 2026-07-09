"""`_needs_knowledge_lookup` — Entscheidungslogik des P24-Auto-Triggers (`api/review_queue.py`).

Reine Funktion (kein HTTP/asyncio-Layer nötig) — der volle Ende-zu-Ende-Fall über den
`confirm`-Endpoint steht bewusst auf der manuellen Smoke-Checkliste des P24-Plans
(`docs/planning/2026-07-01_p24-photofant-integration/README.md`), da `review_queue.py`
physische Datei-Moves auslöst (`materialize_assignment`) und dafür noch kein Test-Geschirr
existiert — dessen Aufbau wäre außerhalb des additiven Scopes dieser Phase.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from photofant.api.review_queue import _needs_knowledge_lookup
from photofant.db.models import Person
from photofant.knowledge.schema import Entity, Owner
from photofant.knowledge.service import KnowledgeService
from photofant.knowledge.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()
    return instance


@pytest.fixture
def service(db_session: Session, vault: Vault) -> KnowledgeService:
    return KnowledgeService(db_session, vault)


def _person(db_session: Session, **overrides: object) -> Person:
    defaults: dict[str, object] = {"id": 42, "name": "Jane Doe", "is_unknown": False}
    defaults.update(overrides)
    person = Person(**defaults)  # type: ignore[arg-type]
    db_session.add(person)
    db_session.commit()
    return person


def test_needs_lookup_true_for_unlinked_named_person(db_session: Session, service: KnowledgeService) -> None:
    person = _person(db_session)
    assert _needs_knowledge_lookup(service, True, person) is True


def test_needs_lookup_false_when_auto_lookup_disabled(db_session: Session, service: KnowledgeService) -> None:
    person = _person(db_session)
    assert _needs_knowledge_lookup(service, False, person) is False


def test_needs_lookup_false_when_person_missing(service: KnowledgeService) -> None:
    assert _needs_knowledge_lookup(service, True, None) is False


def test_needs_lookup_false_when_person_has_no_name(db_session: Session, service: KnowledgeService) -> None:
    person = _person(db_session, name=None)
    assert _needs_knowledge_lookup(service, True, person) is False


def test_needs_lookup_false_when_already_linked(db_session: Session, service: KnowledgeService) -> None:
    person = _person(db_session)
    service.create_entity(
        Entity(id="actors/jane-doe", type="Actor", title="Jane Doe", domain="Movies"), Owner.USER
    )
    service.link_media("actors/jane-doe", "person", person.id, Owner.USER)

    assert _needs_knowledge_lookup(service, True, person) is False
