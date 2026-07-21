"""Validierung von Entity-Frontmatter gegen die Kontrakt-Regeln und die Domäne.

Arbeitet bewusst auf dem **rohen** Frontmatter-Mapping (nicht auf einer schon
typisierten Entity), damit Fehler wie „unbekannter Owner" sauber als Ablehnung
gemeldet werden statt beim Parsen zu crashen. ``validate_entity`` ist der bequeme
Weg für bereits typisierte Objekte (Schreibpfad).
"""
from __future__ import annotations

from typing import Any

from photofant.knowledge.domains import Domain
from photofant.knowledge.parser import entity_to_metadata
from photofant.knowledge.schema import Entity, Owner

_KNOWN_OWNERS: frozenset[str] = frozenset(owner.value for owner in Owner)


class ValidationError(ValueError):
    """Eine oder mehrere Frontmatter-Regeln verletzt."""


def validate_metadata(meta: dict[str, Any], domain: Domain) -> list[str]:
    """Prüft ein rohes Frontmatter-Mapping. Leere Liste = gültig."""
    errors: list[str] = []
    _check_identity(meta, errors)
    _check_type(meta, domain, errors)
    _check_owner(meta, errors)
    _check_confidence(meta, errors)
    _check_relationships(meta, domain, errors)
    _check_attributes(meta, domain, errors)
    return errors


def validate_entity(entity: Entity, domain: Domain) -> list[str]:
    """Prüft eine bereits typisierte Entity (Schreibpfad)."""
    return validate_metadata(entity_to_metadata(entity), domain)


def assert_valid(meta: dict[str, Any], domain: Domain) -> None:
    """Wie ``validate_metadata``, wirft aber ``ValidationError`` bei Fehlern."""
    errors = validate_metadata(meta, domain)
    if errors:
        raise ValidationError("; ".join(errors))


def _check_identity(meta: dict[str, Any], errors: list[str]) -> None:
    entity_id = meta.get("id")
    if not isinstance(entity_id, str) or not entity_id.strip():
        errors.append("Feld 'id' fehlt oder ist leer")
    else:
        prefix, sep, slug = entity_id.partition("/")
        if not sep or not prefix or not slug:
            errors.append(f"'id' muss das Format <type>/<slug> haben, war '{entity_id}'")

    title = meta.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("Feld 'title' fehlt oder ist leer")


def _check_type(meta: dict[str, Any], domain: Domain, errors: list[str]) -> None:
    type_name = meta.get("type")
    if not isinstance(type_name, str) or not type_name.strip():
        errors.append("Feld 'type' fehlt oder ist leer")
    elif not domain.has_entity_type(type_name):
        errors.append(f"Entity-Typ '{type_name}' ist in Domäne '{domain.name}' nicht definiert")


def _check_owner(meta: dict[str, Any], errors: list[str]) -> None:
    owner = meta.get("owner")
    if owner is None:
        return
    if not isinstance(owner, str) or owner not in _KNOWN_OWNERS:
        allowed = ", ".join(sorted(_KNOWN_OWNERS))
        errors.append(f"Unbekannter Owner '{owner}' (erlaubt: {allowed})")


def _check_confidence(meta: dict[str, Any], errors: list[str]) -> None:
    confidence = meta.get("confidence")
    if confidence is None:
        return
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        errors.append(f"'confidence' muss eine Zahl sein, war {confidence!r}")
    elif not 0.0 <= confidence <= 1.0:
        errors.append(f"'confidence' muss zwischen 0.0 und 1.0 liegen, war {confidence}")


def _check_attributes(meta: dict[str, Any], domain: Domain, errors: list[str]) -> None:
    """Merkmale müssen für den Entity-Typ definiert sein — sonst wächst über KI-Läufe
    ein wildes Feld-Sammelsurium heran, das keine Oberfläche mehr anzeigen kann."""
    attributes = meta.get("attributes")
    if attributes is None:
        return
    if not isinstance(attributes, dict):
        errors.append("'attributes' muss ein Mapping sein")
        return

    type_name = meta.get("type")
    defined_keys = (
        {definition.key for definition in domain.fields_for(type_name)}
        if isinstance(type_name, str)
        else set()
    )
    for key, raw in attributes.items():
        if key not in defined_keys:
            errors.append(f"Merkmal '{key}' ist für Typ '{type_name}' nicht definiert")
        if not isinstance(raw, dict):
            errors.append(f"Merkmal '{key}' muss ein Mapping sein, war {raw!r}")
            continue
        _check_attribute_owner(key, raw.get("owner"), errors)
        _check_attribute_confidence(key, raw.get("confidence"), errors)


def _check_attribute_owner(key: str, owner: Any, errors: list[str]) -> None:
    if owner is None:
        return
    if not isinstance(owner, str) or owner not in _KNOWN_OWNERS:
        allowed = ", ".join(sorted(_KNOWN_OWNERS))
        errors.append(f"Merkmal '{key}': unbekannter Owner '{owner}' (erlaubt: {allowed})")


def _check_attribute_confidence(key: str, confidence: Any, errors: list[str]) -> None:
    if confidence is None:
        return
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        errors.append(f"Merkmal '{key}': 'confidence' muss eine Zahl sein, war {confidence!r}")
    elif not 0.0 <= confidence <= 1.0:
        errors.append(
            f"Merkmal '{key}': 'confidence' muss zwischen 0.0 und 1.0 liegen, war {confidence}"
        )


def _check_relationships(meta: dict[str, Any], domain: Domain, errors: list[str]) -> None:
    relationships = meta.get("relationships")
    if relationships is None:
        return
    if not isinstance(relationships, list):
        errors.append("'relationships' muss eine Liste sein")
        return
    for entry in relationships:
        if not isinstance(entry, dict) or "type" not in entry or "target" not in entry:
            errors.append(f"Beziehung braucht 'type' und 'target': {entry!r}")
            continue
        relationship_type = entry["type"]
        if not domain.has_relationship_type(relationship_type):
            errors.append(
                f"Beziehungstyp '{relationship_type}' ist in Domäne '{domain.name}' nicht definiert"
            )
