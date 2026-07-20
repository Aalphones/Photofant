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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from photofant.inference.capabilities import Capability, autonomy_for
from photofant.jobs.knowledge_import_job import enqueue_knowledge_import
from photofant.jobs.knowledge_patch_job import enqueue_knowledge_patch
from photofant.jobs.knowledge_update_job import enqueue_knowledge_update
from photofant.knowledge.schema import MediaLinks, Owner

log = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge/ai")


class AutonomyDto(BaseModel):
    """Autonomie-Stufe (``off`` | ``ask`` | ``auto``) pro KI-Funktion — das Frontend blendet
    die KI-Aktionen bei ``off`` aus (der Backend-Guard unten lehnt sie zusätzlich ab)."""

    knowledge_import: str
    knowledge_update: str
    interview: str


class ImportSuggestionRequest(BaseModel):
    title: str
    domain: str
    type: str
    # Optionaler Personen-/Asset-Kontext (z.B. die Person, deren Wissen angelegt wird).
    person_ids: list[int] = []
    asset_ids: list[int] = []


class ImportSuggestionResponse(BaseModel):
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
    )


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

    media_links = MediaLinks(persons=list(body.person_ids), assets=list(body.asset_ids))
    status = await enqueue_knowledge_import(body.title, body.domain, body.type, media_links)
    return ImportSuggestionResponse(job_id=status.id)


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
