"""Kern-Datenmodell der Wissensbasis — Entity, Relationship, Owner.

Dieses Modul definiert das verbindliche Schema (Kontrakt für P23–P27). Es ist reine
Datenhaltung: kein I/O, kein Parsing, keine Validierung. Frontmatter-Feldreihenfolge
und Ownership-Priorität leben hier als Single Source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Owner(StrEnum):
    """Wer einen Wert zuletzt geschrieben hat — steuert das Überschreibrecht.

    Priorität absteigend: ``user > manual > web > inferred``. Ein Job (``web``/
    ``inferred``) darf einen ``user``-Wert nie überschreiben.
    """

    USER = "user"
    MANUAL = "manual"
    WEB = "web"
    INFERRED = "inferred"


# Überschreib-Priorität — höher darf niedriger überschreiben, niedriger nicht höher.
_OWNER_PRIORITY: dict[Owner, int] = {
    Owner.USER: 3,
    Owner.MANUAL: 2,
    Owner.WEB: 1,
    Owner.INFERRED: 0,
}


def owner_priority(owner: Owner) -> int:
    """Numerische Priorität eines Owners (höher = mehr Rechte)."""
    return _OWNER_PRIORITY[owner]


def owner_can_overwrite(writer: Owner, existing: Owner) -> bool:
    """Darf ``writer`` einen von ``existing`` gehaltenen Wert überschreiben?

    MVP-Regel (Kontrakt): ein Schreibzugriff mit **niedrigerer** Priorität wird
    abgelehnt; gleiche oder höhere Priorität darf überschreiben.
    """
    return _OWNER_PRIORITY[writer] >= _OWNER_PRIORITY[existing]


@dataclass
class MediaLinks:
    """Verknüpfungen einer Entity in die Photofant-Galerie."""

    persons: list[int] = field(default_factory=list)
    assets: list[int] = field(default_factory=list)


@dataclass
class Relationship:
    """Explizite, gerichtete Beziehung zu einer anderen Entity.

    ``target`` ist eine Entity-``id`` (``<type>/<slug>``). Ableitbare Beziehungen
    werden bewusst nicht gespeichert (Dok 020 §6).
    """

    type: str
    target: str


@dataclass
class Attribute:
    """Ein einzelnes Merkmal einer Entity (Geburtstag, Beruf, …) mit eigenem Owner.

    Der Owner sitzt bewusst **pro Merkmal**, nicht nur auf der Entity: ein manuell
    gepflegter Wohnort darf nicht verschwinden, nur weil eine Web-Recherche denselben
    Datensatz anfasst. Die Überschreib-Regel ist dieselbe wie auf Entity-Ebene
    (``owner_can_overwrite``), nur feiner angewendet.
    """

    value: str
    owner: Owner = Owner.INFERRED
    confidence: float = 1.0


def attributes_to_mapping(attributes: dict[str, Attribute]) -> dict[str, dict[str, Any]]:
    """Kanonische Mapping-Form der Merkmale.

    Frontmatter-Block und Cache-Spalte tragen bewusst dieselbe Form — hier steht sie
    einmal, damit die beiden Schreibpfade nicht auseinanderlaufen.
    """
    return {
        key: {
            "value": attribute.value,
            "owner": attribute.owner.value,
            "confidence": attribute.confidence,
        }
        for key, attribute in attributes.items()
    }


@dataclass
class Entity:
    """Eine Wissenseinheit — entspricht genau einer Markdown-Datei.

    Pflichtfelder (``id``/``type``/``title``/``domain``) haben bewusst keinen
    Default: eine Entity ohne sie ist inhaltlich unvollständig und wird vom
    Validator abgelehnt. ``body`` ist der freie Markdown-Artikel unter dem
    Frontmatter. ``attributes`` sind die strukturierten Merkmale (je mit eigenem
    Owner); welche Keys für einen Typ vorgesehen sind, legt die Domäne fest.
    """

    id: str
    type: str
    title: str
    domain: str
    owner: Owner = Owner.INFERRED
    confidence: float = 1.0
    status: str = ""
    aliases: list[str] = field(default_factory=list)
    media_links: MediaLinks = field(default_factory=MediaLinks)
    relationships: list[Relationship] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    attributes: dict[str, Attribute] = field(default_factory=dict)
    body: str = ""

    @property
    def slug(self) -> str:
        """Der Slug-Teil der ``id`` (``<type>/<slug>`` → ``<slug>``) = Dateiname."""
        _, _, slug = self.id.partition("/")
        return slug or self.id

    @property
    def type_prefix(self) -> str:
        """Der Typ-Präfix der ``id`` (``<type>/<slug>`` → ``<type>``)."""
        prefix, sep, _ = self.id.partition("/")
        return prefix if sep else ""
