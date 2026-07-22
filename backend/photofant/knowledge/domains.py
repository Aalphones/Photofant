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
class FieldDef:
    """Ein für einen Entity-Typ vorgesehenes Merkmal.

    ``key`` steht im Frontmatter, ``label`` ist der Anzeigename in der Oberfläche.
    """

    key: str
    label: str
    # Frage fürs Interview (P39 Phase 1). Fehlt sie, wird das Merkmal dort nicht
    # gefragt — bleibt aber ein Merkmal, das Web-Recherche/Handeintrag füllen können.
    question: str | None = None


@dataclass(frozen=True)
class EntityType:
    """Ein Entity-Typ: Anzeigename im Frontmatter + Ordner im Vault + Merkmals-Felder."""

    name: str
    folder: str
    fields: tuple[FieldDef, ...] = ()
    # Bevorzugte Hosts für die Web-Recherche (P39 Phase 1). Schlägt die Domänen-Vorgabe
    # vollständig, wenn nicht leer — siehe Domain.preferred_sources_for.
    preferred_sources: tuple[str, ...] = ()


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
    # Domänen-weite Vorgabe für die Web-Recherche (P39 Phase 1) — greift nur, wenn
    # der Typ selbst keine eigene Liste trägt. Private Domänen tragen hier nichts
    # Wirksames (sie gehen nie ins Netz, siehe preferred_sources_for).
    preferred_sources: tuple[str, ...] = ()

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

    def fields_for(self, type_name: str) -> tuple[FieldDef, ...]:
        """Die Merkmals-Definitionen eines Entity-Typs.

        Unbekannter Typ → leeres Tupel (keine Ausnahme — Aufrufer sind Anzeige-Pfade,
        die nicht wegen eines Tippfehlers in der Domänen-Datei umfallen sollen).
        """
        entity_type = self.entity_types.get(type_name)
        return entity_type.fields if entity_type is not None else ()

    def questions_for(self, type_name: str) -> tuple[FieldDef, ...]:
        """Merkmale des Typs, die eine Interview-Frage tragen, in YAML-Reihenfolge."""
        return tuple(field for field in self.fields_for(type_name) if field.question is not None)

    def preferred_sources_for(self, type_name: str) -> tuple[str, ...]:
        """Bevorzugte Hosts für die Web-Recherche: Typ schlägt Domäne vollständig.

        Private Domänen gehen nie ins Netz (Konzept-ADR-009) — Aufrufer der
        Web-Recherche prüfen ``domain.private`` selbst und rufen diese Methode für
        private Domänen gar nicht erst auf; hier wird nichts zusätzlich verboten,
        nur wie in der Datei geschrieben aufgelöst.
        """
        entity_type = self.entity_types.get(type_name)
        if entity_type is not None and entity_type.preferred_sources:
            return entity_type.preferred_sources
        return self.preferred_sources


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
    preferred_sources = _parse_preferred_sources(raw.get("preferred_sources"), path)
    return Domain(
        name=name,
        entity_types=entity_types,
        relationship_types=relationship_types,
        private=private,
        preferred_sources=preferred_sources,
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
        entity_types[type_name] = EntityType(
            name=type_name,
            folder=folder,
            fields=_parse_fields(entry.get("fields"), path),
            preferred_sources=_parse_preferred_sources(entry.get("preferred_sources"), path),
        )
    return entity_types


def _parse_fields(raw: Any, path: Path) -> tuple[FieldDef, ...]:
    """Optionaler ``fields``-Block eines Entity-Typs.

    Fehlt er, hat der Typ keine Merkmale — das ist ein gültiger Zustand (bestehende
    Domänen-Dateien bleiben ohne Migration lesbar), nur die Vollständigkeit ist dann
    für ihn immer 0.
    """
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise DomainLoadError(f"'fields' muss eine Liste sein: {raw!r} in {path}")

    fields: list[FieldDef] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise DomainLoadError(f"'fields'-Eintrag ist kein Mapping: {entry!r} in {path}")
        key = entry.get("key")
        if not isinstance(key, str) or not key:
            raise DomainLoadError(f"'fields'-Eintrag ohne 'key': {entry!r} in {path}")
        label = entry.get("label")
        if not isinstance(label, str) or not label:
            label = key
        question = entry.get("question")
        if question is not None and not isinstance(question, str):
            raise DomainLoadError(f"'question' muss ein String sein: {entry!r} in {path}")
        fields.append(FieldDef(key=key, label=label, question=question))
    return tuple(fields)


def _parse_preferred_sources(raw: Any, path: Path) -> tuple[str, ...]:
    """Optionale Liste bevorzugter Hosts für die Web-Recherche.

    Fehlt sie, gibt es keine Vorgabe (leeres Tupel). Hosts werden normalisiert:
    ``www.``-Präfix entfernt, klein geschrieben — ``WWW.IMDb.com`` und ``imdb.com``
    sollen als derselbe Host gelten.
    """
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise DomainLoadError(f"'preferred_sources' muss eine Liste sein: {raw!r} in {path}")

    hosts: list[str] = []
    for entry in raw:
        if not isinstance(entry, str) or not entry:
            raise DomainLoadError(f"Ungültiger 'preferred_sources'-Eintrag: {entry!r} in {path}")
        host = entry.strip().lower()
        if host.startswith("www."):
            host = host[len("www.") :]
        hosts.append(host)
    return tuple(hosts)


def _parse_relationship_types(raw: Any, path: Path) -> frozenset[str]:
    if raw is None:
        return frozenset()
    if not isinstance(raw, list):
        raise DomainLoadError(f"'relationship_types' muss eine Liste sein: {path}")
    for entry in raw:
        if not isinstance(entry, str) or not entry:
            raise DomainLoadError(f"Ungültiger 'relationship_types'-Eintrag: {entry!r} in {path}")
    return frozenset(raw)
