"""Graph-Kontext eines Assets für die Empfehlungen (P26 Phase 1).

Ein Asset bekommt seinen Empfehlungs-Kontext aus drei domänen-agnostischen Ebenen,
festgemacht an der Datenstruktur der Wissensbasis (P22) — **nicht** an festen Typnamen
wie „Character"/„Movie", denn die Domäne ist konfigurierbar (Dok 020):

- **persons** — die realen Personen im Bild (aktive ``asset_instance``-Zeilen). Die
  ``_unknown``-Sammelperson zählt bewusst **nicht**: sonst „teilt" jedes noch nicht
  zugeordnete Bild dieselbe Person und ``same_person`` würde wertlos.
- **roles** — die direkt verknüpften Entities (``knowledge_media_links``: das Asset
  direkt **oder** über eine seiner Personen). Eine Verknüpfung = eine „Rolle" (im
  Movies-Beispiel die Figur).
- **films** — die 1-Hop-Beziehungsziele dieser Rollen-Entities
  (``knowledge_relationships``). Eine Kante weiter = der „Film"/Kontext (im
  Movies-Beispiel Film/Serie/Franchise).

Der Kontext wird **gebündelt** für viele Assets auf einmal aufgelöst
(``build_contexts``) — konstant wenige Queries statt N pro Kandidat (P26-Risiko:
Performance bei großer Bibliothek).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import (
    AssetInstance,
    KnowledgeEntity,
    KnowledgeMediaLink,
    KnowledgeRelationship,
    Person,
)


@dataclass
class AssetGraphContext:
    """Die drei Graph-Ebenen eines Assets. ``roles``/``films`` mappen Entity-``id`` → Titel
    (Titel ist die Reason-Chain-Beschriftung; fehlt die Ziel-Entity im Cache, ist der Titel
    die rohe id als Fallback). ``persons`` mappt ``person.id`` → Anzeigename."""

    persons: dict[int, str] = field(default_factory=dict)
    roles: dict[str, str] = field(default_factory=dict)
    films: dict[str, str] = field(default_factory=dict)


def build_context(session: Session, asset_id: int) -> AssetGraphContext:
    """Kontext eines einzelnen Assets (Bequemlichkeits-Wrapper um ``build_contexts``)."""
    return build_contexts(session, [asset_id]).get(asset_id, AssetGraphContext())


def build_contexts(session: Session, asset_ids: list[int]) -> dict[int, AssetGraphContext]:
    """Löst den Graph-Kontext für viele Assets in konstant wenigen Queries auf."""
    ids = list({int(asset_id) for asset_id in asset_ids})
    if not ids:
        return {}

    asset_persons = _persons_per_asset(session, ids)
    all_person_ids = {person_id for persons in asset_persons.values() for person_id in persons}

    direct_role_ids = _direct_asset_entities(session, ids)
    person_role_ids = _person_entities(session, list(all_person_ids))

    roles_per_asset: dict[int, set[str]] = {}
    for asset_id in ids:
        role_ids = set(direct_role_ids.get(asset_id, set()))
        for person_id in asset_persons.get(asset_id, {}):
            role_ids |= person_role_ids.get(person_id, set())
        roles_per_asset[asset_id] = role_ids

    all_role_ids = {role_id for role_ids in roles_per_asset.values() for role_id in role_ids}
    role_to_films = _relationship_targets(session, list(all_role_ids))

    films_per_asset: dict[int, set[str]] = {}
    for asset_id, role_ids in roles_per_asset.items():
        films: set[str] = set()
        for role_id in role_ids:
            films |= role_to_films.get(role_id, set())
        films_per_asset[asset_id] = films

    all_film_ids = {film_id for films in films_per_asset.values() for film_id in films}
    titles = _entity_titles(session, all_role_ids | all_film_ids)

    contexts: dict[int, AssetGraphContext] = {}
    for asset_id in ids:
        contexts[asset_id] = AssetGraphContext(
            persons=asset_persons.get(asset_id, {}),
            roles={role_id: titles.get(role_id, role_id) for role_id in roles_per_asset[asset_id]},
            films={film_id: titles.get(film_id, film_id) for film_id in films_per_asset[asset_id]},
        )
    return contexts


def gather_graph_candidates(session: Session, source_context: AssetGraphContext) -> set[int]:
    """Kandidaten-Assets, die mit dem Quell-Kontext ein Graph-Signal teilen *könnten*.

    Bewusst großzügig (der eigentliche Score entscheidet später): Assets derselben Person,
    Assets derselben Rollen-Entity, und Assets, deren Rolle auf denselben Film zeigt
    (``referencing``-Reverse-Lookup). Die Quelle selbst ist nicht ausgeschlossen — das
    macht der Aufrufer.
    """
    candidates: set[int] = set()
    candidates |= _assets_of_persons(session, list(source_context.persons))

    # Entities, über die geteilte Rollen/Filme laufen: die Quell-Rollen selbst, die Filme
    # selbst (direkt verknüpfte Assets), und alle Entities, die auf einen der Filme zeigen.
    entity_pool: set[str] = set(source_context.roles)
    film_ids = set(source_context.films)
    if film_ids:
        entity_pool |= film_ids
        referencing_rows = session.execute(
            select(KnowledgeRelationship.entity_id).where(KnowledgeRelationship.target.in_(film_ids))
        ).all()
        entity_pool |= {entity_id for (entity_id,) in referencing_rows}

    if entity_pool:
        link_rows = session.execute(
            select(KnowledgeMediaLink.kind, KnowledgeMediaLink.target_id).where(
                KnowledgeMediaLink.entity_id.in_(entity_pool)
            )
        ).all()
        candidates |= {target_id for kind, target_id in link_rows if kind == "asset"}
        linked_person_ids = [target_id for kind, target_id in link_rows if kind == "person"]
        candidates |= _assets_of_persons(session, linked_person_ids)

    return candidates


# ----------------------------------------------------------------------------
# Query-Bausteine — je ein Bulk-Read, keine N+1-Schleifen
# ----------------------------------------------------------------------------


def _persons_per_asset(session: Session, asset_ids: list[int]) -> dict[int, dict[int, str]]:
    """asset_id → {person_id: name} über aktive Instanzen, ohne die ``_unknown``-Sammelperson."""
    rows = session.execute(
        select(AssetInstance.asset_id, Person.id, Person.name)
        .join(Person, Person.id == AssetInstance.person_id)
        .where(AssetInstance.asset_id.in_(asset_ids))
        .where(AssetInstance.deleted_at.is_(None))
        .where(Person.is_unknown.is_(False))
    ).all()
    result: dict[int, dict[int, str]] = defaultdict(dict)
    for asset_id, person_id, name in rows:
        result[asset_id][person_id] = name or f"Person {person_id}"
    return result


def _direct_asset_entities(session: Session, asset_ids: list[int]) -> dict[int, set[str]]:
    """asset_id → direkt verknüpfte Entity-ids (``knowledge_media_links``, kind=asset)."""
    rows = session.execute(
        select(KnowledgeMediaLink.target_id, KnowledgeMediaLink.entity_id)
        .where(KnowledgeMediaLink.kind == "asset")
        .where(KnowledgeMediaLink.target_id.in_(asset_ids))
    ).all()
    result: dict[int, set[str]] = defaultdict(set)
    for target_id, entity_id in rows:
        result[target_id].add(entity_id)
    return result


def _person_entities(session: Session, person_ids: list[int]) -> dict[int, set[str]]:
    """person_id → verknüpfte Entity-ids (``knowledge_media_links``, kind=person)."""
    if not person_ids:
        return {}
    rows = session.execute(
        select(KnowledgeMediaLink.target_id, KnowledgeMediaLink.entity_id)
        .where(KnowledgeMediaLink.kind == "person")
        .where(KnowledgeMediaLink.target_id.in_(person_ids))
    ).all()
    result: dict[int, set[str]] = defaultdict(set)
    for target_id, entity_id in rows:
        result[target_id].add(entity_id)
    return result


def _relationship_targets(session: Session, entity_ids: list[str]) -> dict[str, set[str]]:
    """entity_id → 1-Hop-Beziehungsziele (``knowledge_relationships.target``)."""
    if not entity_ids:
        return {}
    rows = session.execute(
        select(KnowledgeRelationship.entity_id, KnowledgeRelationship.target).where(
            KnowledgeRelationship.entity_id.in_(entity_ids)
        )
    ).all()
    result: dict[str, set[str]] = defaultdict(set)
    for entity_id, target in rows:
        result[entity_id].add(target)
    return result


def _entity_titles(session: Session, entity_ids: set[str]) -> dict[str, str]:
    """entity_id → Titel für die Reason-Chain-Beschriftung (fehlende Entities bleiben außen vor)."""
    if not entity_ids:
        return {}
    rows = session.execute(
        select(KnowledgeEntity.id, KnowledgeEntity.title).where(
            KnowledgeEntity.id.in_(entity_ids)
        )
    ).all()
    return dict(rows)


def _assets_of_persons(session: Session, person_ids: list[int]) -> set[int]:
    """Aktive Assets, die einer der Personen zugeordnet sind."""
    if not person_ids:
        return set()
    rows = session.execute(
        select(AssetInstance.asset_id)
        .where(AssetInstance.person_id.in_(person_ids))
        .where(AssetInstance.deleted_at.is_(None))
    ).all()
    return {asset_id for (asset_id,) in rows}
