"""Cache-Repositories — SQLite-Lesepfad über die Wissensbasis (Namespace ``knowledge_*``).

Schreiben passiert ausschließlich über ``EntityRepository.upsert_from_vault``, gefüttert mit
einer bereits vom Vault gelesenen ``Entity`` — dieses Modul validiert nichts und kennt keine
Ownership-Regeln (die leben im ``KnowledgeService``, Phase 3). Markdown ist die Wahrheit, der
Cache ist jederzeit aus dem Vault identisch neu aufbaubar (Kontrakt-AK).
"""
from __future__ import annotations

from sqlalchemy import Text, cast, or_, select
from sqlalchemy.orm import Session

from photofant.db.models import (
    KnowledgeChangelog,
    KnowledgeEntity,
    KnowledgeMediaLink,
    KnowledgeRelationship,
    KnowledgeSource,
)
from photofant.knowledge.schema import Entity


class EntityRepository:
    """Cache-Schreib-/Lesepfad für Entities inkl. Kind-Zeilen (Relationships/Sources/Media-Links)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_from_vault(self, entity: Entity) -> None:
        """Schreibt eine Entity + Kind-Zeilen in den Cache — voller Ersatz, idempotent.

        Kind-Zeilen werden vor dem Neuschreiben gelöscht statt einzeln abgeglichen: die
        Vault-Entity ist die Wahrheit, ein Merge wäre unnötige Komplexität für einen Cache.
        """
        row = self.session.get(KnowledgeEntity, entity.id)
        if row is None:
            row = KnowledgeEntity(id=entity.id)
            self.session.add(row)
        row.type = entity.type
        row.title = entity.title
        row.domain = entity.domain
        row.owner = entity.owner.value
        row.confidence = entity.confidence
        row.status = entity.status
        row.aliases = list(entity.aliases)

        self._replace_children(entity)

    def _replace_children(self, entity: Entity) -> None:
        self.session.query(KnowledgeRelationship).filter_by(entity_id=entity.id).delete()
        self.session.query(KnowledgeSource).filter_by(entity_id=entity.id).delete()
        self.session.query(KnowledgeMediaLink).filter_by(entity_id=entity.id).delete()

        for relationship in entity.relationships:
            self.session.add(
                KnowledgeRelationship(
                    entity_id=entity.id, type=relationship.type, target=relationship.target,
                )
            )
        for source in entity.sources:
            self.session.add(KnowledgeSource(entity_id=entity.id, source=source))
        for person_id in entity.media_links.persons:
            self.session.add(
                KnowledgeMediaLink(entity_id=entity.id, kind="person", target_id=person_id)
            )
        for asset_id in entity.media_links.assets:
            self.session.add(
                KnowledgeMediaLink(entity_id=entity.id, kind="asset", target_id=asset_id)
            )

    def get(self, entity_id: str) -> KnowledgeEntity | None:
        return self.session.get(KnowledgeEntity, entity_id)

    def get_many(self, entity_ids: list[str]) -> dict[str, KnowledgeEntity]:
        """Bulk-Read mehrerer Entities per id — ein Query statt N für Relationship-Auflösung (P25)."""
        if not entity_ids:
            return {}
        rows = (
            self.session.query(KnowledgeEntity)
            .filter(KnowledgeEntity.id.in_(entity_ids))
            .all()
        )
        return {row.id: row for row in rows}

    def all(self) -> list[KnowledgeEntity]:
        """Alle Cache-Zeilen — Basis für den Reconcile-Abgleich (Zeilen ohne Vault-Datei
        aufspüren)."""
        return list(self.session.execute(select(KnowledgeEntity)).scalars())

    def clear_all(self) -> None:
        """Leert alle ``knowledge_*``-Cache-Tabellen (Kind→Eltern-Reihenfolge).

        Für den vollständigen Rebuild aus dem Vault. Expliziter Cascade in Python, da
        SQLite-FK-Enforcement in dieser App aus ist (siehe ``db/engine.py``) — dasselbe
        Muster wie ``delete``, nur über den gesamten Namespace statt einer Entity.
        """
        self.session.query(KnowledgeRelationship).delete()
        self.session.query(KnowledgeSource).delete()
        self.session.query(KnowledgeMediaLink).delete()
        self.session.query(KnowledgeChangelog).delete()
        self.session.query(KnowledgeEntity).delete()

    def find_by_alias(self, alias: str) -> list[KnowledgeEntity]:
        """Entities, deren Alias-Liste ``alias`` exakt enthält.

        ``aliases`` ist eine JSON-Liste; der Textvergleich sucht die Anführungszeichen-
        umschlossene Form (``"alias"``), damit z.B. ``"DJ"`` nicht zufällig als Teilstring
        von ``"RDJ"`` matcht.
        """
        needle = f'"{alias}"'
        return (
            self.session.query(KnowledgeEntity)
            .filter(cast(KnowledgeEntity.aliases, Text).like(f"%{needle}%"))
            .all()
        )

    def search(
        self, query: str, type: str | None = None, domain: str | None = None
    ) -> list[KnowledgeEntity]:
        """SQL-``LIKE`` über Titel + Alias-Liste (als JSON-Text) — FTS ist laut Kontrakt
        optional, nicht Pflicht."""
        like = f"%{query}%"
        statement = self.session.query(KnowledgeEntity).filter(
            or_(KnowledgeEntity.title.like(like), cast(KnowledgeEntity.aliases, Text).like(like))
        )
        if type is not None:
            statement = statement.filter(KnowledgeEntity.type == type)
        if domain is not None:
            statement = statement.filter(KnowledgeEntity.domain == domain)
        return statement.all()

    def find_linked_entities(self, kind: str, target_ids: list[int]) -> dict[int, KnowledgeEntity]:
        """Reverse-Lookup: ``target_id`` (Person/Asset) → verknüpfte Entity, falls vorhanden.

        Bulk-Variante (ein Query statt N) für Listen-DTOs (P24, analog
        ``_person_instance_counts`` in ``api/persons.py``). Zeigen mehrere Entities auf
        denselben ``target_id`` (Konvention sieht das nicht vor), gewinnt die erste
        gefundene Zeile — deterministisch über die Query-Reihenfolge, kein Sonderfall nötig.
        """
        if not target_ids:
            return {}
        rows = (
            self.session.query(KnowledgeMediaLink, KnowledgeEntity)
            .join(KnowledgeEntity, KnowledgeEntity.id == KnowledgeMediaLink.entity_id)
            .filter(KnowledgeMediaLink.kind == kind, KnowledgeMediaLink.target_id.in_(target_ids))
            .all()
        )
        result: dict[int, KnowledgeEntity] = {}
        for link, entity in rows:
            result.setdefault(link.target_id, entity)
        return result

    def delete(self, entity_id: str) -> None:
        """Löscht die Entity und alle Kind-Zeilen (kein Waise).

        Expliziter Cascade in Python, da SQLite-FK-Enforcement in dieser App nicht aktiviert
        ist (siehe ``db/engine.py``) — gleiches Muster wie ``api/collections.py::delete_collection``.
        """
        self.session.query(KnowledgeRelationship).filter_by(entity_id=entity_id).delete()
        self.session.query(KnowledgeSource).filter_by(entity_id=entity_id).delete()
        self.session.query(KnowledgeMediaLink).filter_by(entity_id=entity_id).delete()
        self.session.query(KnowledgeChangelog).filter_by(entity_id=entity_id).delete()
        self.session.query(KnowledgeEntity).filter_by(id=entity_id).delete()


class RelationshipRepository:
    """Lesepfad für Beziehungen quer über Entities — Graph-Traversal für spätere Phasen
    (z.B. P25 ``get_lore``, P26 Empfehlungen). Schreiben läuft über
    ``EntityRepository.upsert_from_vault``, nicht hier."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def for_entity(self, entity_id: str) -> list[KnowledgeRelationship]:
        """Ausgehende Beziehungen einer Entity (``entity_id`` ist die Quelle)."""
        return self.session.query(KnowledgeRelationship).filter_by(entity_id=entity_id).all()

    def referencing(self, target_id: str) -> list[KnowledgeRelationship]:
        """Eingehende Beziehungen — wer zeigt auf ``target_id`` (Reverse-Lookup)."""
        return self.session.query(KnowledgeRelationship).filter_by(target=target_id).all()
