"""KnowledgeService — orchestriert Vault + Repository + Validator (Kontrakt-Fassade).

Jede Mutation läuft **Markdown-first**: erst der Vault (Wahrheit), dann der Cache
(``EntityRepository.upsert_from_vault``). Die Ownership-Regel (``owner_can_overwrite``)
greift auf zwei Ebenen: **entity-weit** für alle klassischen Schreibpfade (ein Schreibzugriff
mit niedrigerer Priorität als der bestehende ``owner`` wird komplett abgelehnt, ein
erfolgreicher macht den Schreiber zum neuen ``owner``; ``Owner.USER`` erzwingt dabei immer
``confidence = 1.0``) und **pro Merkmal** in ``set_attributes`` (P38 Phase 2) — dort wird
jedes Merkmal einzeln gegen seinen eigenen Owner geprüft und die Entity-Ownership bleibt
unverändert.

Ambiguitäts-Entscheidung (offen laut Phase-2-FINDINGS): ``find_entity`` löst mehrdeutige
Alias-Treffer **nicht** stillschweigend auf (erstes Ergebnis wäre eine stille Falschauswahl
in einer Markdown-first-Wissensbasis) — stattdessen ``AmbiguousEntityError``, der Aufrufer
entscheidet (z.B. UI zeigt eine Auswahl).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from photofant.db.models import KnowledgeEntity, KnowledgeRelationship
from photofant.knowledge.domains import Domain, DomainLoadError, FieldDef
from photofant.knowledge.repository import EntityRepository, RelationshipRepository
from photofant.knowledge.schema import (
    Attribute,
    Entity,
    MediaLinks,
    Owner,
    Relationship,
    owner_can_overwrite,
)
from photofant.knowledge.task_rules import refresh_auto_link_tasks, refresh_completeness_tasks
from photofant.knowledge.tasks import TaskKind, TaskService
from photofant.knowledge.validator import ValidationError, validate_entity
from photofant.knowledge.vault import Vault

# Öffentlich (kein Unterstrich-Präfix): `api/knowledge.py` validiert `PatchEntityRequest.field`
# synchron dagegen, bevor der Korrektur-Job (P25 Phase 3) enqueued wird — eine Feldliste,
# nicht zwei.
PATCHABLE_FIELDS = frozenset(
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


class PrivateDomainError(PermissionError):
    """Web-Recherche gegen eine privat markierte Domäne (Konzept-ADR-009).

    Verteidigung in der Tiefe: die API-Route (P38 Phase 4) blockt bereits mit 422,
    diese Ausnahme fängt den Fall auch dann ab, wenn der Job direkt aufgerufen wird.
    """


@dataclass
class EntityRef:
    """Schlanke Cache-Projektion einer Entity — für ``linked_entity`` auf Person-/Asset-DTOs.

    Bewusst kein voller ``Entity``-Load (kein Vault-Read): die Personen-/Asset-Liste
    braucht nur ``id``/``title``/``type`` für den Chip, nicht den ganzen Markdown-Body.
    ``completeness`` kommt deshalb aus den im Cache gespiegelten Merkmalen (P38 Phase 2),
    nicht aus der Markdown-Datei — sonst öffnete die Personen-Liste pro Zeile eine Datei.
    """

    id: str
    title: str
    type: str
    completeness: float = 0.0


@dataclass
class ResolvedRelationship:
    """Eine ausgehende Beziehung mit aufgelöstem Ziel (Titel + Typ statt der rohen id)."""

    type: str
    target: EntityRef


@dataclass
class Lore:
    """Rückgabe von ``get_lore`` — Entity + 1-Hop-Beziehungen, Medien, Quellen, Franchises.

    Vollform seit P25 Phase 1 (vorher Stub aus P22 Phase 3). ``entity`` ist nur bei
    ``get_lore_for_media`` ohne Verknüpfung ``None`` (200 statt 404 — Kontrakt P25).
    ``franchises`` ist eine Teilmenge von ``relationships`` (Ziel-Typ ``"Franchise"``),
    eigenes Feld, weil das Lore-Panel (Dok 050 §5) Franchises als eigene Sektion zeigt.
    ``related_media`` bleibt roh (nur ids) — der Medien-Join (Thumbnails) passiert in
    der API-Schicht, damit dieses Modul frei von Person-/Asset-/Face-Importen bleibt.
    """

    entity: Entity | None
    relationships: list[ResolvedRelationship]
    franchises: list[EntityRef]
    related_media: MediaLinks
    sources: list[str]


class KnowledgeService:
    """Einzige Mutationsschicht der Wissensbasis (Kontrakt: „jede Persistenz über den Service")."""

    def __init__(self, session: Session, vault: Vault) -> None:
        self.session = session
        self.vault = vault
        self.entities = EntityRepository(session)
        self.relationships = RelationshipRepository(session)
        self._domains: dict[str, Domain] = {}

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
        self._flag_if_incomplete(entity)
        refresh_completeness_tasks(self.session, entity, domain)
        refresh_auto_link_tasks(self.session, self.vault)
        return entity

    def _flag_if_incomplete(self, entity: Entity) -> None:
        """Legt eine ``incomplete_entity``-Aufgabe an, wenn eine frisch angelegte Entity
        außer Typ/Titel noch nichts Inhaltliches trägt (kein Freitext, keine Beziehung) —
        sonst verschwindet eine leer angelegte Entity kommentarlos in der Ablage, ohne
        dass irgendwo ein Hinweis übrig bleibt, sie noch zu befüllen.
        """
        if entity.body.strip() or entity.relationships:
            return
        TaskService(self.session).create_task(
            TaskKind.INCOMPLETE_ENTITY,
            {"entity_id": entity.id, "title": entity.title, "type": entity.type},
        )

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
        refresh_completeness_tasks(self.session, entity, domain)
        return entity

    def completeness_for(self, entity: Entity, domain: Domain | None = None) -> float:
        """Anteil gefüllter Merkmale an den für den Typ definierten.

        Immer berechnet, nie gespeichert — ein persistierter Wert würde gegen die
        Markdown-Wahrheit driften (ADR-025). ``domain`` darf entfallen; dann wird sie
        über den Domänen-Memo dieses Service geholt.
        """
        resolved_domain = domain if domain is not None else self._domain(entity.domain)
        filled_keys = {
            key for key, attribute in entity.attributes.items() if attribute.value.strip()
        }
        return _completeness(filled_keys, resolved_domain.fields_for(entity.type))

    def set_attributes(
        self, entity_id: str, attributes: dict[str, Attribute], owner: Owner
    ) -> tuple[Entity, list[str], list[str]]:
        """Schreibt Merkmale einzeln, jedes gegen seinen eigenen bisherigen Owner geprüft.

        Rückgabe: (gespeicherte Entity, geschriebene Keys, Meldungen zu übersprungenen Keys).
        Übersprungen wird still im Sinne von „kein Fehler" — aber nie stumm: jeder
        übersprungene Key kommt als Klartext-Meldung zurück und landet in der Oberfläche.

        Bewusst **nicht** über ``update_entity``: dessen Ownership-Prüfung arbeitet auf
        Entity-Ebene und würde ein einzelnes ``user``-Merkmal von einem ``web``-Lauf
        mitreißen. Aus demselben Grund bleibt ``entity.owner`` hier unangetastet — ein
        Merkmals-Schreiben ändert nicht die Ownership der ganzen Einheit.

        Changelog-Einträge schreibt der Aufrufer, nicht diese Methode: ``job_id`` und
        Begründung kommen von dort, wie bei den übrigen Schreibpfaden auch.
        """
        entity = self._require_entity(entity_id)
        domain = self.vault.load_domain(entity.domain)
        labels = {
            definition.key: definition.label for definition in domain.fields_for(entity.type)
        }

        written_keys: list[str] = []
        skipped_messages: list[str] = []
        for key, attribute in attributes.items():
            existing = entity.attributes.get(key)
            if existing is not None and not owner_can_overwrite(owner, existing.owner):
                skipped_messages.append(_skip_message(labels.get(key, key), existing.owner))
                continue
            # Leerer Wert heißt „nicht gesetzt" — Key raus, statt die Datei mit
            # Leerzeilen zuwachsen zu lassen.
            if not attribute.value.strip():
                if entity.attributes.pop(key, None) is not None:
                    written_keys.append(key)
                continue
            entity.attributes[key] = attribute
            written_keys.append(key)

        self._validate(entity, domain)
        self.vault.save_entity(entity, domain)
        self.entities.upsert_from_vault(entity)
        refresh_completeness_tasks(self.session, entity, domain)
        return entity, written_keys, skipped_messages

    def validate_patch(self, entity_id: str, patch: dict[str, Any]) -> list[str]:
        """Dry-run: prüft ein vorgeschlagenes Patch gegen die Domäne, ohne zu schreiben.

        Rückgrat der P27-Sicherheitsregel „KI schlägt vor, Nutzer bestätigt" — der
        Import-/Update-Job zeigt das Ergebnis, erst nach Bestätigung schreibt
        ``update_entity``. Leere Liste = valide. Kein Ownership-Check hier; das ist
        die Schreibhürde in ``update_entity``, nicht die Validierung.
        """
        entity = self._require_entity(entity_id)
        candidate = copy.deepcopy(entity)
        _apply_patch(candidate, patch)
        domain = self.vault.load_domain(candidate.domain)
        return validate_entity(candidate, domain)

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

    def link_media(self, entity_id: str, kind: str, target_id: int, owner: Owner) -> Entity:
        """Verknüpft eine Person/ein Asset (``kind`` = ``"person"``/``"asset"``) mit einer Entity.

        Idempotent wie ``create_relationship``: bereits verknüpfte ``target_id`` wird nicht
        doppelt angehängt.
        """
        entity = self._require_entity(entity_id)
        self._check_ownership(entity, owner)

        targets = entity.media_links.persons if kind == "person" else entity.media_links.assets
        if target_id not in targets:
            targets.append(target_id)

        entity.owner = owner
        if owner is Owner.USER:
            entity.confidence = 1.0

        domain = self.vault.load_domain(entity.domain)
        self._validate(entity, domain)
        self.vault.save_entity(entity, domain)
        self.entities.upsert_from_vault(entity)
        return entity

    def unlink_media(self, entity_id: str, kind: str, target_id: int, owner: Owner) -> Entity:
        """Löst eine Person-/Asset-Verknüpfung — kein Fehler, wenn sie nicht existiert."""
        entity = self._require_entity(entity_id)
        self._check_ownership(entity, owner)

        if kind == "person":
            entity.media_links.persons = [
                person_id for person_id in entity.media_links.persons if person_id != target_id
            ]
        else:
            entity.media_links.assets = [
                asset_id for asset_id in entity.media_links.assets if asset_id != target_id
            ]

        entity.owner = owner
        if owner is Owner.USER:
            entity.confidence = 1.0

        domain = self.vault.load_domain(entity.domain)
        self.vault.save_entity(entity, domain)
        self.entities.upsert_from_vault(entity)
        return entity

    def linked_entity_refs(self, kind: str, target_ids: list[int]) -> dict[int, EntityRef]:
        """Bulk-Variante von ``linked_entity_ref`` — ein Query für eine ganze Listen-Ansicht."""
        rows = self.entities.find_linked_entities(kind, target_ids)
        return {
            target_id: EntityRef(
                id=row.id,
                title=row.title,
                type=row.type,
                completeness=self._completeness_from_cache(row),
            )
            for target_id, row in rows.items()
        }

    def linked_entity_ref(self, kind: str, target_id: int) -> EntityRef | None:
        return self.linked_entity_refs(kind, [target_id]).get(target_id)

    def get_lore(self, entity_id: str) -> Lore:
        """Vollständige Lore einer Entity (P25 Phase 1). Wirft ``EntityNotFoundError``."""
        entity = self._require_entity(entity_id)
        resolved = self._resolve_relationships(self.relationships.for_entity(entity_id))
        franchises = [relationship.target for relationship in resolved if relationship.target.type == "Franchise"]
        return Lore(
            entity=entity,
            relationships=resolved,
            franchises=franchises,
            related_media=entity.media_links,
            sources=list(entity.sources),
        )

    def get_lore_bundle(self, targets: list[tuple[str, int]]) -> list[Lore]:
        """Sammelt die Lore mehrerer Medien-Ziele (``(kind, target_id)``) in Eingabe-
        Reihenfolge, dedupliziert nach Entity-``id`` (zwei Personen können dasselbe Wissen
        teilen). Ziele ohne Verknüpfung fallen still heraus — die Liste ist so lang wie es
        Treffer gibt. Ein Bild reicht darüber die darauf gezeigten Personen an ihr Wissen
        durch, statt nur die am Bild selbst verknüpfte Entity zu sehen.
        """
        lores: list[Lore] = []
        seen_entity_ids: set[str] = set()
        for kind, target_id in targets:
            ref = self.linked_entity_ref(kind, target_id)
            if ref is None or ref.id in seen_entity_ids:
                continue
            seen_entity_ids.add(ref.id)
            lores.append(self.get_lore(ref.id))
        return lores

    def get_lore_for_media(self, *, asset_id: int | None = None, person_id: int | None = None) -> Lore:
        """Lore über eine verknüpfte Person/ein verknüpftes Asset (P25 Kontrakt).

        Genau eines von ``asset_id``/``person_id`` wird erwartet (von der Route erzwungen).
        Keine Verknüpfung ist **kein** Fehler — anders als ``get_lore`` liefert das hier eine
        leere Lore (``entity=None``) statt ``EntityNotFoundError`` (Kontrakt: 200, kein 404).
        """
        kind = "person" if person_id is not None else "asset"
        target_id = person_id if person_id is not None else asset_id
        assert target_id is not None  # von der Route erzwungen (genau ein Parameter gesetzt)
        bundle = self.get_lore_bundle([(kind, target_id)])
        if not bundle:
            return Lore(entity=None, relationships=[], franchises=[], related_media=MediaLinks(), sources=[])
        return bundle[0]

    def _resolve_relationships(self, rows: list[KnowledgeRelationship]) -> list[ResolvedRelationship]:
        """Löst Beziehungsziele zu Titel+Typ auf (1 Hop, keine weitere Traversierung — Dok 020 §6).

        Ziel-Entity fehlt im Cache (noch nicht angelegt) → Beziehung bleibt sichtbar, mit der
        rohen id als Titel-Fallback statt die Beziehung stillschweigend zu verschlucken.
        """
        targets = self.entities.get_many([row.target for row in rows])
        resolved: list[ResolvedRelationship] = []
        for row in rows:
            target_row = targets.get(row.target)
            if target_row is not None:
                ref = EntityRef(
                    id=target_row.id,
                    title=target_row.title,
                    type=target_row.type,
                    completeness=self._completeness_from_cache(target_row),
                )
            else:
                ref = EntityRef(id=row.target, title=row.target, type="")
            resolved.append(ResolvedRelationship(type=row.type, target=ref))
        return resolved

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
        domain = self._domain(row.domain)
        placeholder = Entity(id=row.id, type=row.type, title=row.title, domain=row.domain)
        path = self.vault.entity_path(placeholder, domain)
        return self.vault.load_entity(path)

    def _domain(self, domain_name: str) -> Domain:
        """Domäne mit Memo über die Lebensdauer dieses Service (ein Request bzw. ein Job-Lauf).

        Der Lesepfad braucht die Domäne pro Entity — ohne Memo liest eine Listen-Ansicht
        dieselbe YAML einmal je Zeile. Schreibpfade laden bewusst weiter direkt über
        ``vault.load_domain``, damit eine Mutation nie gegen eine veraltete Definition prüft.
        """
        cached = self._domains.get(domain_name)
        if cached is None:
            cached = self.vault.load_domain(domain_name)
            self._domains[domain_name] = cached
        return cached

    def _completeness_from_cache(self, row: KnowledgeEntity) -> float:
        """Vollständigkeit direkt aus der Cache-Zeile — ohne die Markdown-Datei zu öffnen.

        Eine defekte/fehlende Domänen-Datei liefert 0.0 statt einer Ausnahme: die Aufrufer
        sind Listen-Ansichten, die wegen eines Tippfehlers in der Domäne nicht ausfallen sollen.
        """
        try:
            domain = self._domain(row.domain)
        except DomainLoadError:
            return 0.0
        filled_keys = {
            key
            for key, raw in (row.attributes or {}).items()
            if isinstance(raw, dict) and str(raw.get("value", "")).strip()
        }
        return _completeness(filled_keys, domain.fields_for(row.type))


def _completeness(filled_keys: set[str], defined: tuple[FieldDef, ...]) -> float:
    """Gefüllte durch definierte Merkmale. Kein definiertes Merkmal → 0.0 (nicht 1.0):
    „nichts vorgesehen" ist kein vollständiges Profil, sondern ein unkonfigurierter Typ."""
    if not defined:
        return 0.0
    return sum(1 for definition in defined if definition.key in filled_keys) / len(defined)


def _skip_message(label: str, existing_owner: Owner) -> str:
    """Klartext, warum ein Merkmal nicht überschrieben wurde — landet unverändert in der UI."""
    if existing_owner in (Owner.USER, Owner.MANUAL):
        return f"'{label}' bleibt unverändert — der Wert stammt von dir"
    return f"'{label}' bleibt unverändert"


def _apply_patch(entity: Entity, patch: dict[str, Any]) -> None:
    """Wendet ein Partial-Patch auf eine Entity an — mutiert in-place.

    ``id``/``type``/``domain`` sind laut Kontrakt unveränderlich (kein Pfad-Move in
    Phase 3) und werden abgelehnt, statt still ignoriert zu werden.
    """
    immutable_keys = set(patch) - PATCHABLE_FIELDS
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
