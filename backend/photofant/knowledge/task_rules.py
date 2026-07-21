"""task_rules — Ableitungsregeln für automatisch erzeugte Aufgaben (P38 Phase 4).

Eigenes Modul statt in ``service.py``: die Regeln hier sind reine Ableitungen ohne
eigenen Zustand (kein Vault-Schreiben), ``service.py`` ist schon groß. Einhängepunkte:
``KnowledgeService.create_entity``/``set_attributes``/``update_entity`` (Vollständigkeit)
sowie ``api/knowledge_ai.py`` (Übernahme-Route) und ``api/persons.py`` (Namens-Abgleich).
"""
from __future__ import annotations

import difflib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import KnowledgeEntity, KnowledgeMediaLink, Person
from photofant.knowledge.domains import Domain, DomainLoadError
from photofant.knowledge.schema import Entity
from photofant.knowledge.tasks import TaskKind, TaskService, TaskStatus
from photofant.knowledge.vault import Vault

LOW_COMPLETENESS_THRESHOLD = 0.34  # unter einem Drittel gefüllt = „kaum ausgefüllt"
AUTO_LINK_MIN_SCORE = 0.80  # darunter ist ein Namens-Treffer mehr Rauschen als Hilfe


def refresh_completeness_tasks(session: Session, entity: Entity, domain: Domain) -> None:
    """Legt/löst „Feld fehlt" und „kaum ausgefüllt" nach jedem Schreiben auf einer Entity.

    Erst die alten offenen Aufgaben dieser Entity auflösen, **dann** ggf. neu anlegen —
    sonst stapeln sich Varianten, wenn sich die fehlende Feldliste ändert (``create_task``
    ist nur bei exakter Context-Gleichheit idempotent, nicht bei einer geänderten Liste).
    """
    tasks = TaskService(session)
    field_defs = domain.fields_for(entity.type)
    filled_keys = {key for key, attribute in entity.attributes.items() if attribute.value.strip()}
    missing_labels = [
        definition.label for definition in field_defs if definition.key not in filled_keys
    ]

    _resolve_open_for_entity(tasks, TaskKind.MISSING_FIELD, entity.id)
    if missing_labels:
        tasks.create_task(
            TaskKind.MISSING_FIELD,
            {"entity_id": entity.id, "title": entity.title, "fields": missing_labels},
        )

    completeness = (len(filled_keys) / len(field_defs)) if field_defs else 0.0
    _resolve_open_for_entity(tasks, TaskKind.LOW_COMPLETENESS, entity.id)
    if field_defs and filled_keys and completeness < LOW_COMPLETENESS_THRESHOLD:
        tasks.create_task(
            TaskKind.LOW_COMPLETENESS,
            {
                "entity_id": entity.id,
                "title": entity.title,
                "completeness": round(completeness, 2),
            },
        )


def refresh_auto_link_tasks(session: Session, vault: Vault) -> None:
    """Namens-Abgleich zwischen unverknüpften privaten Entities und unverknüpften Personen.

    Reine Ähnlichkeit über ``difflib`` (kein phonetisches Matching — bewusste Grenze,
    der Vorschlag muss ohnehin bestätigt werden). Kein Hintergrund-Lauf: wird synchron
    nach ``create_entity``, nach dem Lösen einer Person-Verknüpfung und nach dem
    Anlegen/Umbenennen einer Person aufgerufen.
    """
    linked_entity_ids = set(
        session.execute(
            select(KnowledgeMediaLink.entity_id).where(KnowledgeMediaLink.kind == "person")
        ).scalars()
    )
    private_entities = [
        row
        for row in session.execute(select(KnowledgeEntity)).scalars()
        if row.id not in linked_entity_ids and _is_private_domain(vault, row.domain)
    ]

    tasks = TaskService(session)
    if not private_entities:
        return

    linked_person_ids = set(
        session.execute(
            select(KnowledgeMediaLink.target_id).where(KnowledgeMediaLink.kind == "person")
        ).scalars()
    )
    unlinked_persons = [
        row
        for row in session.execute(select(Person)).scalars()
        if row.id not in linked_person_ids and row.name is not None and not row.is_unknown
    ]
    if not unlinked_persons:
        for entity_row in private_entities:
            _resolve_open_for_entity(tasks, TaskKind.AUTO_LINK, entity_row.id)
        return

    for entity_row in private_entities:
        _resolve_open_for_entity(tasks, TaskKind.AUTO_LINK, entity_row.id)
        best_person, best_score = _best_name_match(entity_row.title, unlinked_persons)
        if best_person is not None and best_score >= AUTO_LINK_MIN_SCORE:
            tasks.create_task(
                TaskKind.AUTO_LINK,
                {
                    "entity_id": entity_row.id,
                    "title": entity_row.title,
                    "person_id": best_person.id,
                    "person_name": best_person.name,
                    "score": round(best_score, 2),
                },
            )


def _best_name_match(title: str, persons: list[Person]) -> tuple[Person | None, float]:
    best_person: Person | None = None
    best_score = 0.0
    for person in persons:
        score = _name_similarity(title, person.name or "")
        if score > best_score:
            best_person, best_score = person, score
    return best_person, best_score


def _name_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


def _normalize_name(value: str) -> str:
    lowered = value.lower()
    without_punctuation = re.sub(r"[^\w\s]", "", lowered)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def _is_private_domain(vault: Vault, domain_name: str) -> bool:
    try:
        return vault.load_domain(domain_name).private
    except DomainLoadError:
        return False


def _resolve_open_for_entity(tasks: TaskService, kind: TaskKind, entity_id: str) -> None:
    for task in tasks.list_tasks(TaskStatus.OPEN):
        if task.kind == kind.value and task.context.get("entity_id") == entity_id:
            tasks.resolve_task(task.id)
