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
from photofant.knowledge.schema import MediaLinks

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
