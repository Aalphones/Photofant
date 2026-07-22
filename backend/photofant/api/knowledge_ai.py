"""KI-gestützte Wissenspflege (P27) — Endpoints, die einen KI-*Vorschlag* auslösen.

Getrennt vom manuellen Wissens-CRUD (``api/knowledge.py``), weil das hier der abschaltbare
KI-Layer ist (Konzept-ADR-008): jede Funktion ist per ``ai.autonomy`` deaktivierbar, und
bei „aus" verhält sich das System wie das manuelle MVP (P22–P25). Der Vorschlag läuft als
sichtbarer Job über die Queue (GPU-Arbeit serialisiert, Fortschritt im Job-Dock) und trägt
sein Ergebnis über den Job-Stream zum Wizard zurück — geschrieben wird erst durch die
Nutzer-Bestätigung auf dem normalen Speichern-Weg.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from photofant.api.knowledge import EntityRefDto
from photofant.db.session import get_session
from photofant.inference.capabilities import Capability, autonomy_for
from photofant.jobs.interview_job import InterviewAnswer, enqueue_interview
from photofant.jobs.knowledge_discovery_job import enqueue_knowledge_discovery
from photofant.jobs.knowledge_import_job import enqueue_knowledge_import
from photofant.jobs.knowledge_patch_job import enqueue_knowledge_patch
from photofant.jobs.knowledge_update_job import enqueue_knowledge_update
from photofant.knowledge.changelog import ChangelogService
from photofant.knowledge.domains import DomainLoadError
from photofant.knowledge.schema import Attribute, Entity, MediaLinks, Owner, Relationship
from photofant.knowledge.service import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    KnowledgeService,
    OwnershipConflictError,
)
from photofant.settings import patch_settings
from photofant.knowledge.slug import slugify
from photofant.knowledge.task_rules import refresh_completeness_tasks
from photofant.knowledge.validator import ValidationError
from photofant.knowledge.vault import Vault, open_vault

DbSession = Annotated[Session, Depends(get_session)]
VaultDep = Annotated[Vault, Depends(open_vault)]

log = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge/ai")


def _is_private_domain(domain_name: str) -> bool:
    """True, wenn die Domäne als privat markiert ist (Konzept-ADR-009).

    Eine nicht ladbare/unbekannte Domäne gilt als nicht privat — dieser Schalter
    entscheidet nur „privat vs. öffentlich", die eigentliche Domänen-Validierung
    macht der jeweilige Job beim Anlegen des Kandidaten.
    """
    try:
        return open_vault().load_domain(domain_name).private
    except DomainLoadError:
        return False


class AutonomyDto(BaseModel):
    """Autonomie-Stufe (``off`` | ``ask`` | ``auto``) pro KI-Funktion — das Frontend blendet
    die KI-Aktionen bei ``off`` aus (der Backend-Guard unten lehnt sie zusätzlich ab)."""

    knowledge_import: str
    knowledge_update: str
    interview: str
    discovery: str


class ImportSuggestionRequest(BaseModel):
    title: str
    domain: str
    type: str
    # Optionaler Personen-/Asset-Kontext (z.B. die Person, deren Wissen angelegt wird).
    person_ids: list[int] = []
    asset_ids: list[int] = []


class ImportSuggestionResponse(BaseModel):
    job_id: str


class InterviewAnswerDto(BaseModel):
    """Ein beantwortetes Frage-Paar aus dem geführten Interview-Dialog (P27 Phase 4)."""

    question: str
    answer: str


class InterviewSynthesizeRequest(BaseModel):
    """P27 Phase 4 — synthetisiert aus den Interview-Antworten einen Entity-Vorschlag.

    ``domain`` muss privat sein (Konzept-ADR-009); ``person_ids``/``asset_ids`` verknüpfen
    die entstehende Entity optional mit der bekannten Photofant-Person/-Aufnahme."""

    title: str
    domain: str
    type: str
    answers: list[InterviewAnswerDto] = []
    person_ids: list[int] = []
    asset_ids: list[int] = []


class InterviewSynthesizeResponse(BaseModel):
    job_id: str


class UpdateSuggestionRequest(BaseModel):
    """P27 Phase 3 — löst den ``KnowledgeUpdateJob`` für eine bestehende Entity aus."""

    entity_id: str


class UpdateSuggestionResponse(BaseModel):
    job_id: str


class AcceptUpdateSuggestionRequest(BaseModel):
    """P27 Phase 3 — Annahme eines Ergänzungsvorschlags. ``owner`` ist hier bewusst **kein**
    Request-Feld (wie bei ``PatchEntityRequest``): der Schreibpfad ist fix ``inferred``
    (P27-Sicherheitsregel, nie ``user`` — das ist die manuelle Korrektur-Route ``/patch``)."""

    entity_id: str
    body: str
    reason: str


class AcceptUpdateSuggestionResponse(BaseModel):
    job_id: str


@router.get("/autonomy", response_model=AutonomyDto)
def get_autonomy() -> AutonomyDto:
    """Aktuelle Autonomie-Stufe je KI-Funktion — Grundlage fürs Ein-/Ausblenden im Wizard/Panel."""
    return AutonomyDto(
        knowledge_import=autonomy_for(Capability.KNOWLEDGE_IMPORT),
        knowledge_update=autonomy_for(Capability.KNOWLEDGE_UPDATE),
        interview=autonomy_for(Capability.INTERVIEW),
        discovery=autonomy_for(Capability.KNOWLEDGE_DISCOVERY),
    )


class AutonomyPatchRequest(BaseModel):
    """Teil-Update — nur angegebene Felder ändern sich, der Rest bleibt unangetastet."""

    knowledge_import: str | None = None
    knowledge_update: str | None = None
    interview: str | None = None
    discovery: str | None = None


# discovery kennt bewusst kein "ask" — die Bestätigung sitzt im Wizard (Fakten abhaken),
# nicht in diesem Schalter (ADR-031).
_ASK_CAPABLE_MODES = {"off", "ask", "auto"}
_DISCOVERY_MODES = {"off", "auto"}


@router.patch("/autonomy", response_model=AutonomyDto)
def update_autonomy(body: AutonomyPatchRequest) -> AutonomyDto:
    """Setzt die Autonomie-Stufe für eine oder mehrere KI-Funktionen. Schreibt direkt nach
    ``settings.json`` und wirkt sofort — kein Neustart nötig (Einstellungen › KI)."""
    patch: dict[str, str] = {}
    for field, allowed in (
        ("knowledge_import", _ASK_CAPABLE_MODES),
        ("knowledge_update", _ASK_CAPABLE_MODES),
        ("interview", _ASK_CAPABLE_MODES),
        ("discovery", _DISCOVERY_MODES),
    ):
        value = getattr(body, field)
        if value is None:
            continue
        if value not in allowed:
            raise HTTPException(
                status_code=422,
                detail=f"'{field}' erlaubt nur {sorted(allowed)}, nicht '{value}'",
            )
        patch[field] = value

    if patch:
        patch_settings({"ai": {"autonomy": patch}})

    return get_autonomy()


@router.post("/import-suggestion", response_model=ImportSuggestionResponse)
async def request_import_suggestion(body: ImportSuggestionRequest) -> ImportSuggestionResponse:
    """Löst den ``KnowledgeImportJob`` aus — Gemma belegt die Wizard-Felder vor.

    Bei ``ai.autonomy.knowledge_import == "off"`` wird die Aktion abgelehnt (der Wizard bietet
    sie dann gar nicht erst an). Der Vorschlag ist kein Schreibzugriff; das eigentliche Anlegen
    passiert über den bestätigten Speichern-Weg (``POST /knowledge/entities``)."""
    if autonomy_for(Capability.KNOWLEDGE_IMPORT) == "off":
        raise HTTPException(status_code=409, detail="KI-Vorschlag ist in den Einstellungen deaktiviert")
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="Titel ist erforderlich für einen KI-Vorschlag")
    # Privat/öffentlich-Trennung (Konzept-ADR-009): private Personen laufen nie über den
    # Web-Import-Pfad — für sie gibt es den Interview-Mode (Phase 4). Der Wizard bietet den
    # KI-Vorschlag bei einer privaten Domäne gar nicht erst an; dieser Guard ist die
    # Backend-Absicherung dagegen.
    if _is_private_domain(body.domain):
        raise HTTPException(
            status_code=422,
            detail="Private Domänen werden nicht web-importiert — nutze den Interview-Mode",
        )

    media_links = MediaLinks(persons=list(body.person_ids), assets=list(body.asset_ids))
    status = await enqueue_knowledge_import(body.title, body.domain, body.type, media_links)
    return ImportSuggestionResponse(job_id=status.id)


@router.post("/interview", response_model=InterviewSynthesizeResponse)
async def synthesize_interview(body: InterviewSynthesizeRequest) -> InterviewSynthesizeResponse:
    """Löst den ``InterviewJob`` aus — Gemma fasst die Interview-Antworten zu einem
    Beschreibungsvorschlag für eine private Person/ein Haustier zusammen.

    Bei ``ai.autonomy.interview == "off"`` wird die Aktion abgelehnt (der Wizard bietet
    den Interview-Mode dann gar nicht erst an). Die Zieldomäne **muss** privat sein
    (Konzept-ADR-009) — eine öffentliche Domäne läuft über den KI-Import (Phase 2), nicht
    hier. Der Vorschlag ist kein Schreibzugriff; das Anlegen passiert über den bestätigten
    Speichern-Weg (``POST /knowledge/entities`` mit ``owner=user``)."""
    if autonomy_for(Capability.INTERVIEW) == "off":
        raise HTTPException(status_code=409, detail="Der Interview-Mode ist in den Einstellungen deaktiviert")
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="Name ist erforderlich für das Interview")
    if not _is_private_domain(body.domain):
        raise HTTPException(
            status_code=422,
            detail="Der Interview-Mode ist nur für private Domänen — für öffentliches Wissen den KI-Vorschlag nutzen",
        )

    answers = [InterviewAnswer(question=item.question, answer=item.answer) for item in body.answers]
    media_links = MediaLinks(persons=list(body.person_ids), assets=list(body.asset_ids))
    status = await enqueue_interview(body.title, body.domain, body.type, answers, media_links)
    return InterviewSynthesizeResponse(job_id=status.id)


@router.post("/update-suggestion", response_model=UpdateSuggestionResponse)
async def request_update_suggestion(body: UpdateSuggestionRequest) -> UpdateSuggestionResponse:
    """Löst den ``KnowledgeUpdateJob`` aus — Gemma schlägt eine Ergänzung zur bestehenden
    Beschreibung vor (Lore Panel „Ergänzen (KI)"). Bei ``off`` wird die Aktion abgelehnt
    (das Panel bietet sie dann gar nicht erst an)."""
    if autonomy_for(Capability.KNOWLEDGE_UPDATE) == "off":
        raise HTTPException(status_code=409, detail="KI-Ergänzung ist in den Einstellungen deaktiviert")
    if not body.entity_id.strip():
        raise HTTPException(status_code=422, detail="entity_id ist erforderlich")

    status = await enqueue_knowledge_update(body.entity_id)
    return UpdateSuggestionResponse(job_id=status.id)


@router.post("/update-suggestion/accept", response_model=AcceptUpdateSuggestionResponse)
async def accept_update_suggestion(body: AcceptUpdateSuggestionRequest) -> AcceptUpdateSuggestionResponse:
    """Übernimmt einen bestätigten Ergänzungsvorschlag über den P25-Patch-Pfad — mit
    ``owner=inferred`` statt der Nutzer-Korrektur (``/entities/{id}/patch`` setzt fix
    ``user``). Ein user-owned Wert lehnt den Schreibzugriff über die Ownership-Prüfung in
    ``KnowledgeService.update_entity`` ab (der Job endet dann mit einem Fehler-Status)."""
    if autonomy_for(Capability.KNOWLEDGE_UPDATE) == "off":
        raise HTTPException(status_code=409, detail="KI-Ergänzung ist in den Einstellungen deaktiviert")

    status = await enqueue_knowledge_patch(body.entity_id, "body", body.body, body.reason, Owner.INFERRED)
    return AcceptUpdateSuggestionResponse(job_id=status.id)


class DiscoveryRequest(BaseModel):
    """P38 — startet den ``KnowledgeDiscoveryJob``. Das Ergebnis sind Vorschläge (ADR-031);
    geschrieben wird erst über ``/discovery/apply``."""

    entity_id: str
    # P38 Phase 7 — optionaler Hinweis aus dem Web-Suche-Wizard (Beruf, Stadt, Link …),
    # hilft bei Namensvettern. Additiv zum Phase-4-Kontrakt, geht nur in die Suchanfrage ein.
    hint: str | None = None


class DiscoveryResponse(BaseModel):
    job_id: str


def _entity_for_guard(entity_id: str) -> Entity | None:
    """Lädt die Entity nur für den Privat-Domain-Guard — der Job lädt sie danach erneut
    (eigene DB-Session im Thread), doppeltes Lesen ist hier bewusst in Kauf genommen statt
    eine Session über die async-Grenze zu reichen."""
    from photofant.db.session import SessionLocal

    with SessionLocal() as session:
        return KnowledgeService(session, open_vault()).find_entity(entity_id)


@router.post("/discovery", response_model=DiscoveryResponse)
async def request_discovery(body: DiscoveryRequest) -> DiscoveryResponse:
    """Löst den ``KnowledgeDiscoveryJob`` aus — Websuche + Gemma schlagen Fakten vor.

    Bei ``ai.autonomy.discovery == "off"`` wird die Aktion abgelehnt (der Wizard bietet
    „Recherchieren" dann gar nicht erst an). Schreibt nichts (ADR-031) — der Schreibweg
    ist ``POST /discovery/apply``, erst nach Bestätigung der Fakten im Wizard."""
    if autonomy_for(Capability.KNOWLEDGE_DISCOVERY) != "auto":
        raise HTTPException(status_code=409, detail="Web-Recherche ist in den Einstellungen deaktiviert")
    if not body.entity_id.strip():
        raise HTTPException(status_code=422, detail="entity_id ist erforderlich")

    entity = _entity_for_guard(body.entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{body.entity_id}' nicht gefunden")
    if _is_private_domain(entity.domain):
        raise HTTPException(
            status_code=422,
            detail='Private Entitäten werden nie web-recherchiert — nutze „Ergänzen (KI)" (webfrei)',
        )

    status = await enqueue_knowledge_discovery(body.entity_id, body.hint)
    return DiscoveryResponse(job_id=status.id)


class DiscoveryFactDto(BaseModel):
    field: str
    label: str
    value: str
    source: str
    source_url: str
    confidence: float


class DiscoveryEntitySuggestionDto(BaseModel):
    title: str
    type: str
    relationship_type: str
    body: str


class DiscoveryApplyRequest(BaseModel):
    """Bestätigte Auswahl aus dem Wizard (Haken gesetzt) — geschrieben wird nur, was
    hier ankommt, nicht der volle Job-Output."""

    entity_id: str
    facts: list[DiscoveryFactDto] = []
    entity_suggestions: list[DiscoveryEntitySuggestionDto] = []


class DiscoveryApplyResponse(BaseModel):
    written_fields: list[str]
    created_entities: list[EntityRefDto]
    errors: list[str]


@router.post("/discovery/apply", response_model=DiscoveryApplyResponse)
async def apply_discovery(
    body: DiscoveryApplyRequest, session: DbSession, vault: VaultDep
) -> DiscoveryApplyResponse:
    """Schreibt bestätigte Web-Recherche-Fakten — synchron, kein Job mehr (das Modell hat
    schon geantwortet, hier passiert nur noch Schreiben). Dieselben Guards wie
    ``POST /discovery``: die Ziel-Entity kann zwischen Start und Bestätigung deaktiviert
    oder privat geworden sein, also nicht auf den vorangegangenen Job-Lauf vertrauen.

    Jeder einzelne Fakt/Vorschlag schlägt für sich fehl statt die ganze Übernahme
    abzubrechen — ein durch ``owner_can_overwrite`` blockiertes Merkmal oder eine
    Ownership-Kollision auf der Entity selbst (z.B. wenn sie inzwischen ``user``-owned
    ist) landet als Klartext in ``errors``, nicht als 500.
    """
    if autonomy_for(Capability.KNOWLEDGE_DISCOVERY) != "auto":
        raise HTTPException(status_code=409, detail="Web-Recherche ist in den Einstellungen deaktiviert")
    if not body.entity_id.strip():
        raise HTTPException(status_code=422, detail="entity_id ist erforderlich")

    service = KnowledgeService(session, vault)
    entity = service.find_entity(body.entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{body.entity_id}' nicht gefunden")
    domain = vault.load_domain(entity.domain)
    if domain.private:
        raise HTTPException(
            status_code=422,
            detail='Private Entitäten werden nie web-recherchiert — nutze „Ergänzen (KI)" (webfrei)',
        )

    from photofant.jobs.recommendation_job import invalidate_recommendations
    from photofant.recommendation.context import assets_for_entity

    errors: list[str] = []
    written_fields: list[str] = []
    created_entities: list[EntityRefDto] = []

    body_fact = next((fact for fact in body.facts if fact.field == "body"), None)
    attribute_facts = [fact for fact in body.facts if fact.field != "body"]
    source_urls = [fact.source_url for fact in body.facts if fact.source_url]
    merged_sources = sorted(set(entity.sources) | set(source_urls))

    # Beschreibung + Quellen in einem Patch. Läuft auch ohne Beschreibungs-Fakt, sobald
    # neue Quellen dazukommen — sonst würden reine Merkmals-Übernahmen nie in
    # `entity.sources` auftauchen (Kontrakt README „trägt die Quell-URLs in entity.sources").
    if body_fact is not None or merged_sources != sorted(set(entity.sources)):
        patch: dict[str, Any] = {"sources": merged_sources}
        if body_fact is not None:
            patch["body"] = body_fact.value
        validation_errors = service.validate_patch(entity.id, patch)
        if validation_errors:
            errors.extend(validation_errors)
        else:
            old_body = entity.body
            try:
                entity = service.update_entity(entity.id, patch, Owner.WEB)
            except OwnershipConflictError as error:
                errors.append(str(error))
            else:
                if body_fact is not None:
                    written_fields.append("body")
                    ChangelogService(session).record(
                        entity_id=entity.id,
                        field="body",
                        old_value=old_body,
                        new_value=body_fact.value,
                        reason=f"Web-Recherche, von dir bestätigt (Quelle: {body_fact.source})",
                        source=Owner.WEB.value,
                        job_id="",
                    )

    if attribute_facts:
        old_values = {
            fact.field: (
                entity.attributes[fact.field].value if fact.field in entity.attributes else None
            )
            for fact in attribute_facts
        }
        attributes = {
            fact.field: Attribute(value=fact.value, owner=Owner.WEB, confidence=fact.confidence)
            for fact in attribute_facts
        }
        entity, written_keys, skipped_messages = service.set_attributes(entity.id, attributes, Owner.WEB)
        written_fields.extend(written_keys)
        errors.extend(skipped_messages)
        facts_by_field = {fact.field: fact for fact in attribute_facts}
        for key in written_keys:
            fact = facts_by_field[key]
            ChangelogService(session).record(
                entity_id=entity.id,
                field=key,
                old_value=old_values.get(key),
                new_value=fact.value,
                reason=f"Web-Recherche, von dir bestätigt (Quelle: {fact.source})",
                source=Owner.WEB.value,
                job_id="",
            )

    affected_asset_ids: set[int] = set()
    for suggestion in body.entity_suggestions:
        if not domain.has_entity_type(suggestion.type) or not domain.has_relationship_type(
            suggestion.relationship_type
        ):
            errors.append(f"'{suggestion.title}': unbekannter Typ oder Beziehung, übersprungen")
            continue

        matches = [
            candidate
            for candidate in service.search_entities(
                suggestion.title, type=suggestion.type, domain=entity.domain
            )
            if candidate.title.strip().lower() == suggestion.title.strip().lower()
        ]
        if matches:
            target = matches[0]
        else:
            new_entity = Entity(
                id=f"{domain.folder_for(suggestion.type)}/{slugify(suggestion.title)}",
                type=suggestion.type,
                title=suggestion.title,
                domain=entity.domain,
                body=suggestion.body,
            )
            try:
                target = service.create_entity(new_entity, Owner.WEB)
            except (EntityAlreadyExistsError, ValidationError, DomainLoadError) as error:
                errors.append(f"'{suggestion.title}': {error}")
                continue
            created_entities.append(EntityRefDto(id=target.id, title=target.title, type=target.type))

        already_linked = any(
            existing.type == suggestion.relationship_type and existing.target == target.id
            for existing in entity.relationships
        )
        if already_linked:
            continue
        try:
            entity = service.create_relationship(
                entity.id,
                Relationship(type=suggestion.relationship_type, target=target.id),
                Owner.WEB,
            )
        except (EntityNotFoundError, OwnershipConflictError, ValidationError) as error:
            errors.append(f"'{suggestion.title}': {error}")
            continue
        affected_asset_ids |= assets_for_entity(session, entity.id)
        affected_asset_ids |= assets_for_entity(session, target.id)

    if affected_asset_ids:
        invalidate_recommendations(session, affected_asset_ids)

    refresh_completeness_tasks(session, entity, domain)

    return DiscoveryApplyResponse(
        written_fields=written_fields, created_entities=created_entities, errors=errors
    )
