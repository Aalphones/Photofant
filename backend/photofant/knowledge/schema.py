"""Kern-Datenmodell der Wissensbasis — Entity, Relationship, Owner.

Dieses Modul definiert das verbindliche Schema (Kontrakt für P23–P27). Es ist reine
Datenhaltung: kein I/O, kein Parsing, keine Validierung. Frontmatter-Feldreihenfolge
und Ownership-Priorität leben hier als Single Source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


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
class Entity:
    """Eine Wissenseinheit — entspricht genau einer Markdown-Datei.

    Pflichtfelder (``id``/``type``/``title``/``domain``) haben bewusst keinen
    Default: eine Entity ohne sie ist inhaltlich unvollständig und wird vom
    Validator abgelehnt. ``body`` ist der freie Markdown-Artikel unter dem
    Frontmatter.
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
