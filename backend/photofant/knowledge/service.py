"""KnowledgeService — orchestriert Vault + Repository + Validator (Kontrakt-Fassade).

Jede Mutation läuft **Markdown-first**: erst der Vault (Wahrheit), dann der Cache
(``EntityRepository.upsert_from_vault``). Die Ownership-Regel (``owner_can_overwrite``)
ist entity-weit (ein ``owner``-Feld pro Entity, kein Per-Feld-Owner) — ein Schreibzugriff
mit niedrigerer Priorität als der bestehende ``owner`` wird komplett abgelehnt, ein
erfolgreicher Schreibzugriff macht den Schreiber zum neuen ``owner``. ``Owner.USER``
erzwingt dabei immer ``confidence = 1.0`` (Kontrakt).

Ambiguitäts-Entscheidung (offen laut Phase-2-FINDINGS): ``find_entity`` löst mehrdeutige
Alias-Treffer **nicht** stillschweigend auf (erstes Ergebnis wäre eine stille Falschauswahl
in einer Markdown-first-Wissensbasis) — stattdessen ``AmbiguousEntityError``, der Aufrufer
entscheidet (z.B. UI zeigt eine Auswahl).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from photofant.db.models import KnowledgeEntity
from photofant.knowledge.domains import Domain
from photofant.knowledge.repository import EntityRepository, RelationshipRepository
from photofant.knowledge.schema import Entity, MediaLinks, Owner, Relationship, owner_can_overwrite
from photofant.knowledge.validator import ValidationError, validate_entity
from photofant.knowledge.vault import Vault

_PATCHABLE_FIELDS = frozenset(
    {"title", "aliases", "status", "confidence", "media_links", "relationships", "sources", "body"}
)


class EntityNotFoundError(LookupError):
    """Entity-``id`` ist im Cache nicht bekannt."""


class EntityAlreadyExistsError(ValueError):
    """``create_entity`` mit einer bereits vergebenen ``id``."""


class OwnershipConflictError(PermissionError):
    """Schreibversuch mit niedrigerer Owner-Priorität als der bestehende Wert."""


class AmbiguousEntityError(ValueError):
    """Mehrere Entities matchen denselben Alias — keine automatische Auflösung."""


@dataclass
class Lore:
    """Rückgabe von ``get_lore`` — Entity + direkte ausgehende Beziehungen.

    Stub für Phase 3; Ausbau (Graph-Tiefe, Empfehlungen) folgt in P25.
    """

    entity: Entity
    relationships: list[Relationship]


class KnowledgeService:
    """Einzige Mutationsschicht der Wissensbasis (Kontrakt: „jede Persistenz über den Service")."""

    def __init__(self, session: Session, vault: Vault) -> None:
        self.session = session
        self.vault = vault
        self.entities = EntityRepository(session)
        self.relationships = RelationshipRepository(session)

    def create_entity(self, entity: Entity, owner: Owner) -> Entity:
        if self.entities.get(entity.id) is not None:
            raise EntityAlreadyExistsError(f"Entity '{entity.id}' existiert bereits")

        domain = self.vault.load_domain(entity.domain)
        entity.owner = owner
        if owner is Owner.USER:
            entity.confidence = 1.0
        self._validate(entity, domain)

        self.vault.save_entity(entity, domain)
        self.entities.upsert_from_vault(entity)
        return entity

    def find_entity(self, ref: str) -> Entity | None:
        """Löst ``ref`` als ``id`` (exakt) oder Alias auf. ``None`` = nicht gefunden."""
        row = self.entities.get(ref)
        if row is None:
            matches = self.entities.find_by_alias(ref)
            if not matches:
                return None
            if len(matches) > 1:
                raise AmbiguousEntityError(
                    f"Alias '{ref}' ist mehrdeutig: {[match.id for match in matches]}"
                )
            row = matches[0]
        return self._load_from_cache_row(row)

    def search_entities(
        self, query: str, type: str | None = None, domain: str | None = None
    ) -> list[Entity]:
        rows = self.entities.search(query, type=type, domain=domain)
        return [self._load_from_cache_row(row) for row in rows]

    def update_entity(self, entity_id: str, patch: dict[str, Any], owner: Owner) -> Entity:
        entity = self._require_entity(entity_id)
        self._check_ownership(entity, owner)

        _apply_patch(entity, patch)
        entity.owner = owner
        if owner is Owner.USER:
            entity.confidence = 1.0

        domain = self.vault.load_domain(entity.domain)
        self._validate(entity, domain)

        self.vault.save_entity(entity, domain)
        self.entities.upsert_from_vault(entity)
        return entity

    def delete_entity(self, entity_id: str) -> None:
        entity = self._require_entity(entity_id)
        domain = self.vault.load_domain(entity.domain)
        self.vault.delete_entity(entity, domain)
        self.entities.delete(entity_id)

    def create_relationship(self, entity_id: str, relationship: Relationship, owner: Owner) -> Entity:
        entity = self._require_entity(entity_id)
        self._check_ownership(entity, owner)

        domain = self.vault.load_domain(entity.domain)
        if not domain.has_relationship_type(relationship.type):
            raise ValidationError(
                f"Beziehungstyp '{relationship.type}' ist in Domäne '{domain.name}' nicht definiert"
            )
        already_present = any(
            existing.type == relationship.type and existing.target == relationship.target
            for existing in entity.relationships
        )
        if not already_present:
            entity.relationships.append(relationship)

        entity.owner = owner
        if owner is Owner.USER:
            entity.confidence = 1.0

        self.vault.save_entity(entity, domain)
        self.entities.upsert_from_vault(entity)
        return entity

    def remove_relationship(
        self, entity_id: str, relationship_type: str, target: str, owner: Owner
    ) -> Entity:
        entity = self._require_entity(entity_id)
        self._check_ownership(entity, owner)

        entity.relationships = [
            existing
            for existing in entity.relationships
            if not (existing.type == relationship_type and existing.target == target)
        ]
        entity.owner = owner
        if owner is Owner.USER:
            entity.confidence = 1.0

        domain = self.vault.load_domain(entity.domain)
        self.vault.save_entity(entity, domain)
        self.entities.upsert_from_vault(entity)
        return entity

    def get_lore(self, entity_id: str) -> Lore:
        """Stub: Entity + direkte ausgehende Beziehungen. Ausbau P25."""
        entity = self._require_entity(entity_id)
        outgoing = self.relationships.for_entity(entity_id)
        return Lore(
            entity=entity,
            relationships=[Relationship(type=row.type, target=row.target) for row in outgoing],
        )

    def _check_ownership(self, entity: Entity, writer: Owner) -> None:
        if not owner_can_overwrite(writer, entity.owner):
            raise OwnershipConflictError(
                f"'{writer.value}' darf '{entity.owner.value}'-Werte auf '{entity.id}' nicht überschreiben"
            )

    def _validate(self, entity: Entity, domain: Domain) -> None:
        errors = validate_entity(entity, domain)
        if errors:
            raise ValidationError("; ".join(errors))

    def _require_entity(self, entity_id: str) -> Entity:
        row = self.entities.get(entity_id)
        if row is None:
            raise EntityNotFoundError(f"Entity '{entity_id}' nicht gefunden")
        return self._load_from_cache_row(row)

    def _load_from_cache_row(self, row: KnowledgeEntity) -> Entity:
        """Liest die volle Entity (inkl. Body) aus dem Vault — der Cache liefert nur den Pfad."""
        domain = self.vault.load_domain(row.domain)
        placeholder = Entity(id=row.id, type=row.type, title=row.title, domain=row.domain)
        path = self.vault.entity_path(placeholder, domain)
        return self.vault.load_entity(path)


def _apply_patch(entity: Entity, patch: dict[str, Any]) -> None:
    """Wendet ein Partial-Patch auf eine Entity an — mutiert in-place.

    ``id``/``type``/``domain`` sind laut Kontrakt unveränderlich (kein Pfad-Move in
    Phase 3) und werden abgelehnt, statt still ignoriert zu werden.
    """
    immutable_keys = set(patch) - _PATCHABLE_FIELDS
    if immutable_keys:
        raise ValidationError(f"Felder nicht änderbar: {', '.join(sorted(immutable_keys))}")

    if "title" in patch:
        entity.title = str(patch["title"])
    if "aliases" in patch:
        entity.aliases = list(patch["aliases"])
    if "status" in patch:
        entity.status = str(patch["status"])
    if "confidence" in patch:
        entity.confidence = float(patch["confidence"])
    if "media_links" in patch:
        raw_media_links = patch["media_links"] or {}
        entity.media_links = MediaLinks(
            persons=list(raw_media_links.get("persons", [])),
            assets=list(raw_media_links.get("assets", [])),
        )
    if "relationships" in patch:
        raw_relationships = patch["relationships"] or []
        entity.relationships = [
            Relationship(type=raw["type"], target=raw["target"]) for raw in raw_relationships
        ]
    if "sources" in patch:
        entity.sources = list(patch["sources"])
    if "body" in patch:
        entity.body = str(patch["body"])
