"""Domänen — die Liste erlaubter Entity- und Relationship-Typen.

Die Engine kennt keinen Typ hart. Jede Domäne (``domains/<domain>.yaml``) legt fest,
welche Entity-Typen es gibt und in welchen Ordner sie geschrieben werden, sowie
welche Beziehungstypen erlaubt sind. Ausgeliefert wird die Beispiel-Domäne „Movies".
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class DomainLoadError(ValueError):
    """Domänen-Datei fehlt, ist kein gültiges YAML oder unvollständig."""


@dataclass(frozen=True)
class EntityType:
    """Ein Entity-Typ: Anzeigename im Frontmatter + Ordner im Vault."""

    name: str
    folder: str


@dataclass
class Domain:
    """Erlaubte Entity- und Relationship-Typen einer Domäne."""

    name: str
    entity_types: dict[str, EntityType]
    relationship_types: frozenset[str]
    # Privat markierte Domänen (``private: true`` in der YAML) tragen Wissen über
    # reale, dem Nutzer bekannte Personen/Haustiere. Sie sind vom Web-Import-Pfad
    # ausgeschlossen (Konzept-ADR-009): so eine Entity darf nie mit Fremd-/Web-Wissen
    # angereichert werden, nur aus dem Interview-Mode (P27 Phase 4) entstehen.
    private: bool = False

    def has_entity_type(self, type_name: str) -> bool:
        return type_name in self.entity_types

    def has_relationship_type(self, relationship_type: str) -> bool:
        return relationship_type in self.relationship_types

    def folder_for(self, type_name: str) -> str:
        """Vault-Ordner (Plural) für einen Entity-Typ.

        Kein Hand-Pluralisieren — der Ordner steht explizit in der Domänen-Datei.
        """
        entity_type = self.entity_types.get(type_name)
        if entity_type is None:
            raise DomainLoadError(
                f"Entity-Typ '{type_name}' ist in Domäne '{self.name}' nicht definiert"
            )
        return entity_type.folder


def load_domain(path: Path) -> Domain:
    """Lädt und parst eine Domänen-Datei. Wirft ``DomainLoadError`` bei jedem Problem."""
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise DomainLoadError(f"Domänen-Datei nicht lesbar: {path} ({error})") from error

    try:
        raw: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as error:
        raise DomainLoadError(f"Domänen-Datei ist kein gültiges YAML: {path} ({error})") from error

    if not isinstance(raw, dict):
        raise DomainLoadError(f"Domänen-Datei muss ein YAML-Mapping sein: {path}")

    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise DomainLoadError(f"Domänen-Datei ohne gültiges 'name'-Feld: {path}")

    entity_types = _parse_entity_types(raw.get("entity_types"), path)
    relationship_types = _parse_relationship_types(raw.get("relationship_types"), path)
    private = _parse_private(raw.get("private"), path)
    return Domain(
        name=name,
        entity_types=entity_types,
        relationship_types=relationship_types,
        private=private,
    )


def _parse_private(raw: Any, path: Path) -> bool:
    """Optionaler ``private``-Schalter — fehlt er, ist die Domäne öffentlich."""
    if raw is None:
        return False
    if not isinstance(raw, bool):
        raise DomainLoadError(f"'private' muss true/false sein, war {raw!r} in {path}")
    return raw


def _parse_entity_types(raw: Any, path: Path) -> dict[str, EntityType]:
    if not isinstance(raw, list) or not raw:
        raise DomainLoadError(f"Domäne braucht mindestens einen 'entity_types'-Eintrag: {path}")

    entity_types: dict[str, EntityType] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            raise DomainLoadError(f"'entity_types'-Eintrag ist kein Mapping: {entry!r} in {path}")
        type_name = entry.get("name")
        folder = entry.get("folder")
        if not isinstance(type_name, str) or not type_name:
            raise DomainLoadError(f"'entity_types'-Eintrag ohne 'name': {entry!r} in {path}")
        if not isinstance(folder, str) or not folder:
            raise DomainLoadError(f"Entity-Typ '{type_name}' ohne 'folder' in {path}")
        entity_types[type_name] = EntityType(name=type_name, folder=folder)
    return entity_types


def _parse_relationship_types(raw: Any, path: Path) -> frozenset[str]:
    if raw is None:
        return frozenset()
    if not isinstance(raw, list):
        raise DomainLoadError(f"'relationship_types' muss eine Liste sein: {path}")
    for entry in raw:
        if not isinstance(entry, str) or not entry:
            raise DomainLoadError(f"Ungültiger 'relationship_types'-Eintrag: {entry!r} in {path}")
    return frozenset(raw)
