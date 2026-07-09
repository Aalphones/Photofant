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
from sqlalchemy.orm import Session

from photofant.db.session import get_session
from photofant.knowledge.domains import Domain, DomainLoadError
from photofant.knowledge.schema import Entity, MediaLinks, Owner, Relationship
from photofant.knowledge.service import (
    AmbiguousEntityError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
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
    body: str

    @classmethod
    def from_entity(cls, entity: Entity) -> EntityDto:
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
            body=entity.body,
        )


class EntityTypeDto(BaseModel):
    name: str
    folder: str


class DomainDto(BaseModel):
    name: str
    entity_types: list[EntityTypeDto]
    relationship_types: list[str]

    @classmethod
    def from_domain(cls, domain: Domain) -> DomainDto:
        return cls(
            name=domain.name,
            entity_types=[
                EntityTypeDto(name=entity_type.name, folder=entity_type.folder)
                for entity_type in domain.entity_types.values()
            ],
            relationship_types=sorted(domain.relationship_types),
        )


class LoreDto(BaseModel):
    entity: EntityDto
    relationships: list[RelationshipDto]

    @classmethod
    def from_lore(cls, lore: Lore) -> LoreDto:
        return cls(
            entity=EntityDto.from_entity(lore.entity),
            relationships=[
                RelationshipDto(type=relationship.type, target=relationship.target)
                for relationship in lore.relationships
            ],
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


def _service(session: Session, vault: Vault) -> KnowledgeService:
    return KnowledgeService(session, vault)


def _parse_owner(value: str) -> Owner:
    try:
        return Owner(value)
    except ValueError as error:
        allowed = ", ".join(owner.value for owner in Owner)
        raise HTTPException(
            status_code=422, detail=f"Unbekannter Owner '{value}' (erlaubt: {allowed})"
        ) from error


def _search(service: KnowledgeService, q: str, type: str | None, domain: str | None) -> list[EntityDto]:
    return [EntityDto.from_entity(entity) for entity in service.search_entities(q, type=type, domain=domain)]


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
    return EntityDto.from_entity(entity)


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
    return EntityDto.from_entity(entity)


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
    return EntityDto.from_entity(entity)


@router.get("/entities/{entity_id:path}/lore", response_model=LoreDto)
async def get_lore(entity_id: str, session: DbSession, vault: VaultDep) -> LoreDto:
    service = _service(session, vault)
    try:
        lore = service.get_lore(entity_id)
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return LoreDto.from_lore(lore)


@router.get("/entities/{entity_id:path}", response_model=EntityDto)
async def get_entity(entity_id: str, session: DbSession, vault: VaultDep) -> EntityDto:
    service = _service(session, vault)
    try:
        entity = service.find_entity(entity_id)
    except AmbiguousEntityError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' nicht gefunden")
    return EntityDto.from_entity(entity)


@router.patch("/entities/{entity_id:path}", response_model=EntityDto)
async def update_entity(
    entity_id: str, body: UpdateEntityRequest, session: DbSession, vault: VaultDep
) -> EntityDto:
    service = _service(session, vault)
    owner = _parse_owner(body.owner)
    try:
        entity = service.update_entity(entity_id, body.to_patch(), owner)
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except OwnershipConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ValidationError, DomainLoadError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return EntityDto.from_entity(entity)


@router.delete("/entities/{entity_id:path}", status_code=204)
async def delete_entity(entity_id: str, session: DbSession, vault: VaultDep) -> Response:
    service = _service(session, vault)
    try:
        service.delete_entity(entity_id)
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=204)
