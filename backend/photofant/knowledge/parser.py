"""Parser/Serializer zwischen Entity-Objekt und Markdown-Datei.

Verantwortlich nur für die Umwandlung (Struktur), nicht für die inhaltliche Prüfung
— die macht ``validator.py``. Frontmatter wird über ``python-frontmatter`` gelesen
und geschrieben; der Body bleibt dabei unverändert (verlustfreier Round-Trip).
"""
from __future__ import annotations

from typing import Any

import frontmatter

from photofant.knowledge.schema import (
    Attribute,
    Entity,
    MediaLinks,
    Owner,
    Relationship,
    attributes_to_mapping,
)

# Feldreihenfolge im serialisierten Frontmatter — bewusst festgelegt für lesbare,
# stabile Dateien (Kontrakt-Reihenfolge aus der Plan-README).
_FIELD_ORDER: tuple[str, ...] = (
    "id",
    "type",
    "title",
    "aliases",
    "status",
    "owner",
    "confidence",
    "domain",
    "media_links",
    "relationships",
    "sources",
    "attributes",
)


class EntityParseError(ValueError):
    """Frontmatter ist strukturell defekt (z.B. unbekannter Owner, nicht-numerische Confidence)."""


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Zerlegt eine Markdown-Datei in (Frontmatter-Mapping, Body). Keine Coercion."""
    post = frontmatter.loads(text)
    return dict(post.metadata), post.content


def entity_to_metadata(entity: Entity) -> dict[str, Any]:
    """Baut das Frontmatter-Mapping in kanonischer Feldreihenfolge."""
    return {
        "id": entity.id,
        "type": entity.type,
        "title": entity.title,
        "aliases": list(entity.aliases),
        "status": entity.status,
        "owner": entity.owner.value,
        "confidence": entity.confidence,
        "domain": entity.domain,
        "media_links": {
            "persons": list(entity.media_links.persons),
            "assets": list(entity.media_links.assets),
        },
        "relationships": [
            {"type": relationship.type, "target": relationship.target}
            for relationship in entity.relationships
        ],
        "sources": list(entity.sources),
        "attributes": attributes_to_mapping(entity.attributes),
    }


def metadata_to_entity(meta: dict[str, Any], body: str) -> Entity:
    """Baut aus Frontmatter-Mapping + Body eine typisierte Entity.

    Erwartet strukturell gültige Metadaten (Owner bekannt, Confidence numerisch).
    Für nicht vertrauenswürdige Eingaben vorher ``validator.validate_metadata`` fahren.
    """
    return Entity(
        id=_as_str(meta.get("id")),
        type=_as_str(meta.get("type")),
        title=_as_str(meta.get("title")),
        domain=_as_str(meta.get("domain")),
        owner=_as_owner(meta.get("owner", Owner.INFERRED.value)),
        confidence=_as_confidence(meta.get("confidence", 1.0)),
        status=_as_str(meta.get("status")),
        aliases=[_as_str(alias) for alias in _as_list(meta.get("aliases"))],
        media_links=_as_media_links(meta.get("media_links")),
        relationships=_as_relationships(meta.get("relationships")),
        sources=[_as_str(source) for source in _as_list(meta.get("sources"))],
        attributes=_as_attributes(meta.get("attributes")),
        body=body,
    )


def parse_entity(text: str) -> Entity:
    """Vollständiger Parse einer Markdown-Datei in eine Entity."""
    meta, body = split_frontmatter(text)
    return metadata_to_entity(meta, body)


def serialize_entity(entity: Entity) -> str:
    """Serialisiert eine Entity zu Markdown (Frontmatter + Body), Reihenfolge stabil."""
    post = frontmatter.Post(entity.body, **entity_to_metadata(entity))
    # sort_keys=False bewahrt die kanonische Feldreihenfolge (auch verschachtelt).
    return frontmatter.dumps(post, sort_keys=False)


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_owner(value: Any) -> Owner:
    try:
        return Owner(str(value))
    except ValueError as error:
        raise EntityParseError(f"Unbekannter Owner: {value!r}") from error


def _as_confidence(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EntityParseError(f"Confidence muss eine Zahl sein, war {value!r}")
    return float(value)


def _as_media_links(value: Any) -> MediaLinks:
    if not isinstance(value, dict):
        return MediaLinks()
    return MediaLinks(
        persons=[_as_int(person) for person in _as_list(value.get("persons"))],
        assets=[_as_int(asset) for asset in _as_list(value.get("assets"))],
    )


def _as_attributes(value: Any) -> dict[str, Attribute]:
    """Liest den ``attributes``-Block.

    Fehlt er komplett (alle vor P38 geschriebenen Dateien), ist das kein Fehler —
    leeres Mapping, kein Migrationszwang.
    """
    if not isinstance(value, dict):
        return {}
    attributes: dict[str, Attribute] = {}
    for key, raw in value.items():
        if not isinstance(raw, dict):
            raise EntityParseError(f"Merkmal '{key}' ist kein Mapping: {raw!r}")
        attributes[str(key)] = Attribute(
            value=_as_str(raw.get("value")),
            owner=_as_owner(raw.get("owner", Owner.INFERRED.value)),
            confidence=_as_confidence(raw.get("confidence", 1.0)),
        )
    return attributes


def _as_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EntityParseError(f"Media-Link-ID muss ganzzahlig sein, war {value!r}")
    return value


def _as_relationships(value: Any) -> list[Relationship]:
    relationships: list[Relationship] = []
    for entry in _as_list(value):
        if not isinstance(entry, dict):
            raise EntityParseError(f"Beziehung ist kein Mapping: {entry!r}")
        relationship_type = entry.get("type")
        target = entry.get("target")
        if not isinstance(relationship_type, str) or not isinstance(target, str):
            raise EntityParseError(f"Beziehung braucht 'type' und 'target': {entry!r}")
        relationships.append(Relationship(type=relationship_type, target=target))
    return relationships
