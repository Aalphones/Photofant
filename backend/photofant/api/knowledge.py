"""Wissensbasis-Endpoint (P22 Phase 3) — CRUD auf Entities + Beziehungen, Lore-Stub.

Schreibrouten nehmen ``owner`` optional entgegen (Default ``"user"`` — die UI ist der
einzige heutige REST-Schreiber). Automatisierte Schreiber (Jobs, ab P24) laufen zwar
in-process im Job-Queue-Worker und könnten ``KnowledgeService`` direkt aufrufen, die
Plan-Smoke-Checkliste prüft die Ownership-Regel aber explizit per REST-``PATCH`` mit
``owner=inferred`` — deshalb bleibt ``owner`` hier ein echter, wenn auch optionaler,
Request-Parameter statt serverseitig hart auf ``user`` fixiert zu sein.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from photofant.db.models import Asset, AssetInstance, Face, KnowledgeChangelog, Person
from photofant.db.session import get_session
from photofant.jobs.knowledge_patch_job import enqueue_knowledge_patch
from photofant.knowledge.changelog import ChangelogService
from photofant.knowledge.domains import Domain, DomainLoadError
from photofant.knowledge.schema import Entity, MediaLinks, Owner, Relationship
from photofant.knowledge.service import (
    PATCHABLE_FIELDS,
    AmbiguousEntityError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    EntityRef,
    KnowledgeService,
    Lore,
    OwnershipConflictError,
)
from photofant.knowledge.validator import ValidationError
from photofant.knowledge.vault import Vault, open_vault

router = APIRouter(prefix="/knowledge")

DbSession = Annotated[Session, Depends(get_session)]
VaultDep = Annotated[Vault, Depends(open_vault)]

log = logging.getLogger(__name__)


class MediaLinksDto(BaseModel):
    persons: list[int] = []
    assets: list[int] = []


class RelationshipDto(BaseModel):
    type: str
    target: str


class AttributeDto(BaseModel):
    """Ein Merkmal mit eigenem Owner (P38 Phase 2)."""

    value: str
    owner: str
    confidence: float


class EntityDto(BaseModel):
    id: str
    type: str
    title: str
    domain: str
    owner: str
    confidence: float
    status: str
    aliases: list[str]
    media_links: MediaLinksDto
    relationships: list[RelationshipDto]
    sources: list[str]
    attributes: dict[str, AttributeDto] = {}
    # Anteil gefüllter Merkmale — immer berechnet, nie gespeichert (ADR-025/032).
    completeness: float = 0.0
    body: str

    @classmethod
    def from_entity(cls, entity: Entity, completeness: float = 0.0) -> EntityDto:
        return cls(
            id=entity.id,
            type=entity.type,
            title=entity.title,
            domain=entity.domain,
            owner=entity.owner.value,
            confidence=entity.confidence,
            status=entity.status,
            aliases=list(entity.aliases),
            media_links=MediaLinksDto(
                persons=list(entity.media_links.persons), assets=list(entity.media_links.assets)
            ),
            relationships=[
                RelationshipDto(type=relationship.type, target=relationship.target)
                for relationship in entity.relationships
            ],
            sources=list(entity.sources),
            attributes={
                key: AttributeDto(
                    value=attribute.value,
                    owner=attribute.owner.value,
                    confidence=attribute.confidence,
                )
                for key, attribute in entity.attributes.items()
            },
            completeness=completeness,
            body=entity.body,
        )


class FieldDefDto(BaseModel):
    """Ein für einen Entity-Typ vorgesehenes Merkmal (Domänen-Definition, P38 Phase 2)."""

    key: str
    label: str


class EntityTypeDto(BaseModel):
    name: str
    folder: str
    fields: list[FieldDefDto] = []


class DomainDto(BaseModel):
    name: str
    entity_types: list[EntityTypeDto]
    relationship_types: list[str]
    private: bool = False

    @classmethod
    def from_domain(cls, domain: Domain) -> DomainDto:
        return cls(
            name=domain.name,
            entity_types=[
                EntityTypeDto(
                    name=entity_type.name,
                    folder=entity_type.folder,
                    fields=[
                        FieldDefDto(key=definition.key, label=definition.label)
                        for definition in entity_type.fields
                    ],
                )
                for entity_type in domain.entity_types.values()
            ],
            relationship_types=sorted(domain.relationship_types),
            private=domain.private,
        )


class EntityRefDto(BaseModel):
    id: str
    title: str
    type: str
    # Aus den im Cache gespiegelten Merkmalen — die Personen-Karte und die Wissens-
    # Übersicht zeigen den Prozentwert damit ohne zweiten Request (P38 Phase 2).
    completeness: float = 0.0


class ResolvedRelationshipDto(BaseModel):
    type: str
    target: EntityRefDto


class MediaRefDto(BaseModel):
    """Ein per ``media_links`` verknüpftes Person-/Asset-Bild samt Thumbnail (Medien-Join)."""

    kind: str  # "person" | "asset"
    id: int
    thumbnail_url: str
    label: str | None = None


class LoreDto(BaseModel):
    """Vollform seit P25 Phase 1. ``entity`` ist nur bei ``GET .../lore?asset_id=/person_id=``
    ohne Verknüpfung ``None`` (Kontrakt: 200 statt 404)."""

    entity: EntityDto | None
    relationships: list[ResolvedRelationshipDto]
    franchises: list[EntityRefDto]
    related_media: list[MediaRefDto]
    sources: list[str]

    @classmethod
    def from_lore(
        cls, lore: Lore, related_media: list[MediaRefDto], completeness: float = 0.0
    ) -> LoreDto:
        return cls(
            entity=(
                EntityDto.from_entity(lore.entity, completeness)
                if lore.entity is not None
                else None
            ),
            relationships=[
                ResolvedRelationshipDto(
                    type=relationship.type,
                    target=_entity_ref_dto(relationship.target),
                )
                for relationship in lore.relationships
            ],
            franchises=[_entity_ref_dto(ref) for ref in lore.franchises],
            related_media=related_media,
            sources=list(lore.sources),
        )


class CreateEntityRequest(BaseModel):
    id: str
    type: str
    title: str
    domain: str
    aliases: list[str] = []
    status: str = ""
    owner: str = Owner.USER.value
    confidence: float = 1.0
    media_links: MediaLinksDto = MediaLinksDto()
    relationships: list[RelationshipDto] = []
    sources: list[str] = []
    body: str = ""

    def to_entity(self) -> Entity:
        return Entity(
            id=self.id,
            type=self.type,
            title=self.title,
            domain=self.domain,
            aliases=list(self.aliases),
            status=self.status,
            confidence=self.confidence,
            media_links=MediaLinks(persons=list(self.media_links.persons), assets=list(self.media_links.assets)),
            relationships=[
                Relationship(type=relationship.type, target=relationship.target)
                for relationship in self.relationships
            ],
            sources=list(self.sources),
            body=self.body,
        )


class UpdateEntityRequest(BaseModel):
    owner: str = Owner.USER.value
    title: str | None = None
    aliases: list[str] | None = None
    status: str | None = None
    confidence: float | None = None
    media_links: MediaLinksDto | None = None
    relationships: list[RelationshipDto] | None = None
    sources: list[str] | None = None
    body: str | None = None

    def to_patch(self) -> dict[str, Any]:
        patch = self.model_dump(exclude_unset=True, exclude={"owner"})
        if "media_links" in patch and patch["media_links"] is not None:
            patch["media_links"] = {
                "persons": patch["media_links"]["persons"],
                "assets": patch["media_links"]["assets"],
            }
        if "relationships" in patch and patch["relationships"] is not None:
            patch["relationships"] = [
                {"type": entry["type"], "target": entry["target"]} for entry in patch["relationships"]
            ]
        return patch


class CreateRelationshipRequest(BaseModel):
    type: str
    target: str
    owner: str = Owner.USER.value


class PatchEntityRequest(BaseModel):
    """„Das stimmt nicht"-Korrektur (P25 Phase 3) — Einzelfeld-Patch mit Grund.

    ``owner`` ist hier bewusst **kein** Request-Parameter (anders als bei
    ``UpdateEntityRequest``): diese Route ist die Nutzer-Korrektur, der Owner steht
    fest auf ``user`` (Kontrakt). KI-Korrekturvorschläge (P27) rufen den Job-Pfad
    (``enqueue_knowledge_patch``) direkt mit einem anderen Owner auf, nicht über
    diese REST-Route.
    """

    field: str
    value: Any
    reason: str


class PatchJobResponse(BaseModel):
    job_id: str


class ChangelogEntryDto(BaseModel):
    id: int
    entity_id: str
    field: str
    old_value: Any
    new_value: Any
    reason: str
    source: str
    job_id: str
    created_at: str

    @classmethod
    def from_row(cls, row: KnowledgeChangelog) -> ChangelogEntryDto:
        return cls(
            id=row.id,
            entity_id=row.entity_id,
            field=row.field,
            old_value=row.old_value,
            new_value=row.new_value,
            reason=row.reason,
            source=row.source,
            job_id=row.job_id,
            created_at=row.created_at.isoformat(),
        )


def _service(session: Session, vault: Vault) -> KnowledgeService:
    return KnowledgeService(session, vault)


def _entity_ref_dto(ref: EntityRef) -> EntityRefDto:
    return EntityRefDto(
        id=ref.id, title=ref.title, type=ref.type, completeness=ref.completeness
    )


def _parse_owner(value: str) -> Owner:
    try:
        return Owner(value)
    except ValueError as error:
        allowed = ", ".join(owner.value for owner in Owner)
        raise HTTPException(
            status_code=422, detail=f"Unbekannter Owner '{value}' (erlaubt: {allowed})"
        ) from error


def _search(service: KnowledgeService, q: str, type: str | None, domain: str | None) -> list[EntityDto]:
    return [
        EntityDto.from_entity(entity, service.completeness_for(entity))
        for entity in service.search_entities(q, type=type, domain=domain)
    ]


def _portrait_face_ids(session: Session, person_ids: list[int]) -> dict[int, int]:
    """Best face (highest score, NULLs last) je ``person_id`` — scoped Variante von
    ``api/persons.py::_person_portrait_face_ids`` (dort ungefiltert für die Personen-Liste,
    hier auf die verknüpften ids der Lore begrenzt statt einen Vollscan zu duplizieren)."""
    if not person_ids:
        return {}
    ranked = (
        select(
            Face.person_id,
            Face.id,
            func.row_number()
            .over(partition_by=Face.person_id, order_by=Face.score.desc().nulls_last())
            .label("rank"),
        )
        .where(Face.person_id.in_(person_ids))
        .subquery()
    )
    rows = session.execute(select(ranked.c.person_id, ranked.c.id).where(ranked.c.rank == 1)).all()
    return dict(rows)


def _resolve_media_refs(session: Session, media_links: MediaLinks) -> list[MediaRefDto]:
    """Löst ``media_links`` (rohe Person-/Asset-ids) zu anzeigbaren Refs mit Thumbnail auf.

    Personen ohne Portrait (keine Gesichts-Aufnahme) werden ausgelassen — kein Bild zum
    Zeigen ist kein Fehler, aber auch kein Eintrag in "Eigene Bilder".
    """
    refs: list[MediaRefDto] = []
    if media_links.persons:
        portrait_face_ids = _portrait_face_ids(session, media_links.persons)
        persons = session.query(Person).filter(Person.id.in_(media_links.persons)).all()
        for person in persons:
            face_id = portrait_face_ids.get(person.id)
            if face_id is None:
                continue
            refs.append(
                MediaRefDto(
                    kind="person", id=person.id, thumbnail_url=f"/api/faces/{face_id}/thumbnail",
                    label=person.name,
                )
            )
    if media_links.assets:
        assets = session.query(Asset).filter(Asset.id.in_(media_links.assets)).all()
        for asset in assets:
            refs.append(
                MediaRefDto(
                    kind="asset", id=asset.id, thumbnail_url=f"/api/assets/{asset.id}/thumbnail",
                )
            )
    return refs


def _person_ids_on_asset(session: Session, asset_id: int) -> list[int]:
    """Personen, die auf einem Bild gezeigt werden. Die kanonische Zugehörigkeit läuft über
    ``asset_instance`` (dieselbe Quelle wie die Bildzählung pro Person), nicht über rohe
    Gesichter — die existieren auch ohne zugewiesene Person. Deterministisch sortiert."""
    rows = session.execute(
        select(AssetInstance.person_id)
        .where(AssetInstance.asset_id == asset_id, AssetInstance.deleted_at.is_(None))
        .distinct()
        .order_by(AssetInstance.person_id)
    ).all()
    return [int(row[0]) for row in rows]


@router.get("/lore", response_model=list[LoreDto])
async def get_lore_for_media(
    session: DbSession,
    vault: VaultDep,
    asset_id: int | None = None,
    person_id: int | None = None,
) -> list[LoreDto]:
    """Gebündeltes Wissen zu einem Bild oder einer Person (P25, erweitert).

    Genau einer von ``asset_id``/``person_id`` ist erforderlich. Für eine Person kommt
    höchstens ein Block zurück (ihr verknüpftes Wissen). Für ein Bild werden die darauf
    gezeigten Personen zu ihrem Wissen aufgelöst — plus ein evtl. direkt am Bild
    verknüpftes Wissen —, sodass mehrere Blöcke entstehen können. Keine Verknüpfung ist
    kein Fehler, sondern eine leere Liste (200, kein 404)."""
    if (asset_id is None) == (person_id is None):
        raise HTTPException(
            status_code=422, detail="Genau einer von asset_id/person_id ist erforderlich"
        )
    service = _service(session, vault)

    if person_id is not None:
        targets: list[tuple[str, int]] = [("person", person_id)]
    else:
        assert asset_id is not None  # durch die 422-Prüfung oben garantiert
        targets = [
            ("asset", asset_id),
            *(("person", pid) for pid in _person_ids_on_asset(session, asset_id)),
        ]

    lores = service.get_lore_bundle(targets)
    return [
        LoreDto.from_lore(
            lore,
            _resolve_media_refs(session, lore.related_media),
            service.completeness_for(lore.entity) if lore.entity is not None else 0.0,
        )
        for lore in lores
    ]


@router.get("/domains", response_model=list[DomainDto])
async def list_domains(vault: VaultDep) -> list[DomainDto]:
    """Verfügbare Domänen mit ihren erlaubten Entity-/Beziehungstypen.

    Nicht im P22-Kontrakt vorgesehen — der Wizard (P23 Phase 2) braucht die
    Typ-Liste für seinen Pflicht-Dropdown, es gab dafür noch keinen Endpoint.
    Reines Lesen der Domänen-Configs, keine Cache-Beteiligung.
    """
    return [DomainDto.from_domain(domain) for domain in vault.list_domains()]


@router.post("/entities", response_model=EntityDto, status_code=201)
async def create_entity(body: CreateEntityRequest, session: DbSession, vault: VaultDep) -> EntityDto:
    service = _service(session, vault)
    owner = _parse_owner(body.owner)
    try:
        entity = service.create_entity(body.to_entity(), owner)
    except EntityAlreadyExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ValidationError, DomainLoadError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return EntityDto.from_entity(entity, service.completeness_for(entity))


@router.get("/entities", response_model=list[EntityDto])
async def list_entities(
    session: DbSession,
    vault: VaultDep,
    q: str = "",
    type: str | None = None,
    domain: str | None = None,
) -> list[EntityDto]:
    return _search(_service(session, vault), q, type, domain)


@router.get("/entities/search", response_model=list[EntityDto])
async def search_entities_endpoint(
    session: DbSession,
    vault: VaultDep,
    q: str,
    type: str | None = None,
    domain: str | None = None,
) -> list[EntityDto]:
    return _search(_service(session, vault), q, type, domain)


# Route-Reihenfolge ist bewusst: `{entity_id:path}` matcht auch Slashes (IDs haben die
# Form `<type>/<slug>`), Starlette prüft Routen in Registrierungsreihenfolge und nimmt
# den ersten vollen (Pfad UND Methode) Treffer. Die Suffix-Routen (`/relationships`,
# `/lore`) müssen deshalb VOR der bloßen `/entities/{entity_id}`-Route stehen — sonst
# verschluckt deren `.*`-Pattern jede tiefere GET/DELETE-Anfrage auf dieselbe Methode,
# bevor die spezifischere Route je geprüft wird.


@router.post("/entities/{entity_id:path}/relationships", response_model=EntityDto)
async def create_relationship(
    entity_id: str, body: CreateRelationshipRequest, session: DbSession, vault: VaultDep
) -> EntityDto:
    service = _service(session, vault)
    owner = _parse_owner(body.owner)
    try:
        entity = service.create_relationship(
            entity_id, Relationship(type=body.type, target=body.target), owner
        )
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except OwnershipConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ValidationError, DomainLoadError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    from photofant.jobs.recommendation_job import invalidate_recommendations
    from photofant.recommendation.context import assets_for_entity

    invalidate_recommendations(session, assets_for_entity(session, entity_id))
    return EntityDto.from_entity(entity, service.completeness_for(entity))


@router.delete("/entities/{entity_id:path}/relationships", response_model=EntityDto)
async def remove_relationship(
    entity_id: str,
    type: str,
    target: str,
    session: DbSession,
    vault: VaultDep,
    owner: str = Owner.USER.value,
) -> EntityDto:
    service = _service(session, vault)
    try:
        entity = service.remove_relationship(entity_id, type, target, _parse_owner(owner))
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except OwnershipConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    from photofant.jobs.recommendation_job import invalidate_recommendations
    from photofant.recommendation.context import assets_for_entity

    invalidate_recommendations(session, assets_for_entity(session, entity_id))
    return EntityDto.from_entity(entity, service.completeness_for(entity))


@router.post("/entities/{entity_id:path}/patch", response_model=PatchJobResponse)
async def patch_entity(entity_id: str, body: PatchEntityRequest) -> PatchJobResponse:
    """Löst den ``KnowledgePatchJob`` aus (P25 Phase 3) — läuft asynchron über die
    Job Queue (Kontrakt Dok 030: jede Mutation ist ein Job), Fortschritt/Fehler laufen
    über den Job-Dock/SSE-Stream wie bei ``POST /lookup``. Existenz der Entity und
    Ownership werden im Job selbst geprüft, nicht hier synchron — nur die Feldliste
    wird vorab validiert, damit ein Tippfehler nicht erst als Job-Error auftaucht."""
    if body.field not in PATCHABLE_FIELDS:
        allowed = ", ".join(sorted(PATCHABLE_FIELDS))
        raise HTTPException(
            status_code=422, detail=f"Feld '{body.field}' nicht patchbar (erlaubt: {allowed})"
        )
    status = await enqueue_knowledge_patch(entity_id, body.field, body.value, body.reason, Owner.USER)
    return PatchJobResponse(job_id=status.id)


@router.get("/entities/{entity_id:path}/changelog", response_model=list[ChangelogEntryDto])
async def get_entity_changelog(entity_id: str, session: DbSession) -> list[ChangelogEntryDto]:
    """Explainability-Historie einer Entity (P25 Phase 3) — geteilte Payload mit P26
    Phase 3 (Warum?-Popover)."""
    return [ChangelogEntryDto.from_row(row) for row in ChangelogService(session).list_for_entity(entity_id)]


@router.get("/entities/{entity_id:path}/lore", response_model=LoreDto)
async def get_lore(entity_id: str, session: DbSession, vault: VaultDep) -> LoreDto:
    service = _service(session, vault)
    try:
        lore = service.get_lore(entity_id)
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    media_refs = _resolve_media_refs(session, lore.related_media)
    completeness = service.completeness_for(lore.entity) if lore.entity is not None else 0.0
    return LoreDto.from_lore(lore, media_refs, completeness)


@router.get("/entities/{entity_id:path}", response_model=EntityDto)
async def get_entity(entity_id: str, session: DbSession, vault: VaultDep) -> EntityDto:
    service = _service(session, vault)
    try:
        entity = service.find_entity(entity_id)
    except AmbiguousEntityError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' nicht gefunden")
    return EntityDto.from_entity(entity, service.completeness_for(entity))


@router.patch("/entities/{entity_id:path}", response_model=EntityDto)
async def update_entity(
    entity_id: str, body: UpdateEntityRequest, session: DbSession, vault: VaultDep
) -> EntityDto:
    from photofant.jobs.recommendation_job import invalidate_recommendations
    from photofant.recommendation.context import assets_for_entity

    service = _service(session, vault)
    owner = _parse_owner(body.owner)
    patch = body.to_patch()
    needs_invalidation = bool({"relationships", "media_links"} & patch.keys())
    before_ids = assets_for_entity(session, entity_id) if needs_invalidation else set()
    try:
        entity = service.update_entity(entity_id, patch, owner)
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except OwnershipConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ValidationError, DomainLoadError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    if needs_invalidation:
        invalidate_recommendations(session, before_ids | assets_for_entity(session, entity_id))
    return EntityDto.from_entity(entity, service.completeness_for(entity))


@router.delete("/entities/{entity_id:path}", status_code=204)
async def delete_entity(entity_id: str, session: DbSession, vault: VaultDep) -> Response:
    from photofant.jobs.recommendation_job import invalidate_recommendations
    from photofant.recommendation.context import assets_for_entity

    service = _service(session, vault)
    affected = assets_for_entity(session, entity_id)
    try:
        service.delete_entity(entity_id)
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    invalidate_recommendations(session, affected)
    return Response(status_code=204)
