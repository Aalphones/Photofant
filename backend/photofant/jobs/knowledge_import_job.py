"""KnowledgeImportJob (P27 Phase 2) — Gemma füllt einen Entity-Vorschlag für den Wizard.

Der Nutzer klickt im Wizard „KI-Vorschlag": dieser Job fordert die Fähigkeit
``KNOWLEDGE_IMPORT`` an (nie ein Modell — ADR-027), lässt Gemma aus dem vorhandenen
Kontext (Name, Typ, Domäne) einen Beschreibungstext erzeugen, baut daraus einen
**Kandidaten** und prüft ihn gegen die Domäne (P22-Validator). Nichts wird geschrieben:
das Ergebnis reist über den Job-Stream zurück und belegt die Wizard-Felder als
bestätigungspflichtigen Vorschlag vor. Erst der normale Wizard-Speichern-Weg
(``POST /knowledge/entities`` mit ``owner=user``) schreibt — die P27-Sicherheitsregel
„KI schlägt vor, Nutzer bestätigt" (Konzept-ADR-006).

Reine Sackgasse wie ``KnowledgeLookupJob``/``KnowledgePatchJob``: löst keine Folge-Jobs aus.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from photofant.inference.capabilities import Capability, generate
from photofant.inference.prompt_library import PromptLibrary
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.knowledge.schema import Entity, MediaLinks, Owner
from photofant.knowledge.validator import validate_entity
from photofant.knowledge.vault import open_vault

log = logging.getLogger(__name__)

# Rohe Textgenerierung liefert keine kalibrierte Confidence (FINDINGS: GenerationResult.
# confidence bleibt None). Ein KI-Import-Vorschlag ist per Definition unbestätigt — er
# bekommt eine feste, mittlere „inferred"-Confidence, die im Explainability-Element als
# „Vorschlag, ungeprüft" ablesbar ist. Der Nutzer hebt sie durch Bestätigen auf 1.0 (der
# Speichern-Weg setzt owner=user → confidence=1.0).
SUGGESTION_CONFIDENCE = 0.5

_PROMPT_NAME = "knowledge_import"


def _slugify(value: str) -> str:
    """Baut aus dem Titel einen id-Slug (nur fürs Validieren des Kandidaten — der Wizard
    baut die endgültige id beim Speichern selbst neu, dieser Wert erreicht den Vault nie)."""
    lowered = value.strip().lower()
    ascii_only = lowered.encode("ascii", "ignore").decode("ascii")
    hyphenated = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return hyphenated or "vorschlag"


def _build_user_prompt(title: str, entity_type: str, domain_name: str) -> str:
    """Der konkrete Kontext-Turn für Gemma. Die Rollen-/Regelanweisung kommt als System-
    Teil aus der Prompt-Library; hier nur die Fakten des aktuellen Falls."""
    return (
        f"Entity-Titel: {title}\n"
        f"Typ: {entity_type}\n"
        f"Domäne: {domain_name}\n\n"
        "Schreibe einen kurzen, sachlichen Beschreibungsabsatz (2-4 Sätze) für diese "
        "Entity. Nur belegbare Fakten; keine Aufzählung, kein Markdown-Titel."
    )


def _run_import(
    status: JobStatus, title: str, domain_name: str, entity_type: str, media_links: MediaLinks
) -> None:
    prompt = PromptLibrary().get(_PROMPT_NAME)
    if prompt is None:
        raise RuntimeError(
            f"Prompt '{_PROMPT_NAME}' nicht gefunden — Prompt-Library prüfen (ai.promptLibraryPath)"
        )

    job_queue.update(status, progress=0.3, state=JobState.RUNNING)
    generation = generate(
        Capability.KNOWLEDGE_IMPORT,
        _build_user_prompt(title, entity_type, domain_name),
        system=prompt.text,
        prompt_version=prompt.version,
    )
    body = generation.text.strip()
    if not body:
        raise RuntimeError(
            "Das Modell lieferte keinen Vorschlag — Modell nicht verfügbar oder leere Antwort"
        )

    job_queue.update(status, progress=0.8, state=JobState.RUNNING)
    vault = open_vault()
    domain = vault.load_domain(domain_name)
    candidate = Entity(
        id=f"{domain.folder_for(entity_type)}/{_slugify(title)}",
        type=entity_type,
        title=title,
        domain=domain_name,
        owner=Owner.INFERRED,
        confidence=SUGGESTION_CONFIDENCE,
        media_links=media_links,
        body=body,
    )
    validation_errors = validate_entity(candidate, domain)

    explainability: dict[str, Any] = {
        "model_id": generation.model_id,
        "capability": generation.capability,
        "prompt_version": generation.prompt_version,
        "duration_ms": generation.duration_ms,
        "confidence": SUGGESTION_CONFIDENCE,
        "reason": f"Vorschlag von Gemma auf Basis von Titel, Typ und Domäne ({domain_name}).",
    }

    if validation_errors:
        # Ungültiger Vorschlag wird abgewiesen, nicht belegt (AK Phase 2). Das Frontend
        # zeigt die Gründe, statt die Felder mit Unbrauchbarem zu füllen.
        result: dict[str, Any] = {
            "suggestion": None,
            "explainability": explainability,
            "validation_errors": validation_errors,
        }
        log.info("knowledge_import: Vorschlag für '%s' abgewiesen (%d Fehler)", title, len(validation_errors))
    else:
        result = {
            "suggestion": {
                "title": title,
                "type": entity_type,
                "domain": domain_name,
                "aliases": [],
                "relationships": [],
                "body": body,
            },
            "explainability": explainability,
            "validation_errors": [],
        }
        log.info("knowledge_import: Vorschlag für '%s' erzeugt (%.0f ms)", title, generation.duration_ms)

    job_queue.set_result(status, result)


async def run_knowledge_import_job(
    status: JobStatus, title: str, domain_name: str, entity_type: str, media_links: MediaLinks
) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_import, status, title, domain_name, entity_type, media_links)


async def enqueue_knowledge_import(
    title: str, domain_name: str, entity_type: str, media_links: MediaLinks | None = None
) -> JobStatus:
    links = media_links or MediaLinks()

    async def _factory(status: JobStatus) -> None:
        await run_knowledge_import_job(status, title, domain_name, entity_type, links)

    return await job_queue.enqueue(
        kind=JobKind.KNOWLEDGE_IMPORT,
        label=f"KI-Vorschlag: {title}",
        coro_factory=_factory,
    )
