"""InterviewJob (P27 Phase 4) — Gemma fasst einen geführten Interview-Dialog über eine
PRIVATE Person/ein Haustier zu einem Entity-Vorschlag zusammen.

Der Nutzer beantwortet im Wizard einen festen Fragen-Satz (Wer ist die Person?
Beziehung? Wichtige Ereignisse? …), eine Frage nach der anderen — kein freies Chat
(AK Phase 4). Nach der letzten Antwort läuft dieser Job **einmal**: er fordert die
Fähigkeit ``INTERVIEW`` an (nie ein Modell — ADR-027), lässt Gemma aus den gesammelten
Antworten einen Beschreibungsabsatz **synthetisieren** (nur zusammenfassen, nie Fakten
erfinden — Konzept-ADR-009) und prüft den Kandidaten gegen die Domäne (P22-Validator).

Strikte Privat/Öffentlich-Trennung (Konzept-ADR-009): die ``INTERVIEW``-Fähigkeit hat
kein Such-/Web-Tool (siehe ``inference/tools.py``), Gemma sieht ausschließlich die
Interview-Antworten. Die Zieldomäne muss privat sein — das erzwingt die auslösende
Route (``api/knowledge_ai.py``), nicht dieser Job.

Nichts wird geschrieben: das Ergebnis reist über den Job-Stream zurück und zeigt sich
im Wizard als bestätigungspflichtige Zusammenfassung. Erst der normale Speichern-Weg
(``POST /knowledge/entities`` mit ``owner=user``) legt die Entity an — die
P27-Sicherheitsregel „KI schlägt vor, Nutzer bestätigt". Reine Sackgasse wie der
Import-Job: löst keine Folge-Jobs aus.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

from photofant.inference.capabilities import Capability, generate
from photofant.inference.prompt_library import PromptLibrary
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.knowledge.schema import Entity, MediaLinks, Owner
from photofant.knowledge.validator import validate_entity
from photofant.knowledge.vault import open_vault

log = logging.getLogger(__name__)

# Die Fakten stammen direkt vom Nutzer (er hat sie im Interview genannt), nicht aus
# einer Modell-Inferenz — anders als beim Import-/Update-Vorschlag. Der Kandidat trägt
# deshalb volle Confidence; bestätigt wird er trotzdem manuell (Sicherheitsregel).
INTERVIEW_CONFIDENCE = 1.0

_PROMPT_NAME = "interview"


@dataclass(frozen=True)
class InterviewAnswer:
    """Ein beantwortetes Interview-Frage-Paar aus dem geführten Dialog."""

    question: str
    answer: str


def _slugify(value: str) -> str:
    """Baut aus dem Titel einen id-Slug (nur fürs Validieren des Kandidaten — der Wizard
    baut die endgültige id beim Speichern selbst neu, dieser Wert erreicht den Vault nie)."""
    lowered = value.strip().lower()
    ascii_only = lowered.encode("ascii", "ignore").decode("ascii")
    hyphenated = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return hyphenated or "person"


def _build_user_prompt(title: str, answers: list[InterviewAnswer]) -> str:
    """Der Kontext-Turn für Gemma: die Interview-Antworten als Protokoll. Die Rollen-/
    Regelanweisung (nur zusammenfassen, nie erfinden, kein Web) kommt als System-Teil aus
    der Prompt-Library; hier nur die konkreten Antworten dieses Falls."""
    transcript = "\n".join(
        f"Frage: {answer.question}\nAntwort: {answer.answer.strip()}"
        for answer in answers
        if answer.answer.strip()
    )
    return (
        f"Name: {title}\n\n"
        "Interview-Antworten:\n"
        f"{transcript or '(keine Antworten)'}\n\n"
        "Fasse diese Antworten zu einem zusammenhängenden Beschreibungsabsatz zusammen."
    )


def _run_interview(
    status: JobStatus,
    title: str,
    domain_name: str,
    entity_type: str,
    media_links: MediaLinks,
    answers: list[InterviewAnswer],
) -> None:
    prompt = PromptLibrary().get(_PROMPT_NAME)
    if prompt is None:
        raise RuntimeError(
            f"Prompt '{_PROMPT_NAME}' nicht gefunden — Prompt-Library prüfen (ai.promptLibraryPath)"
        )

    job_queue.update(status, progress=0.3, state=JobState.RUNNING)
    generation = generate(
        Capability.INTERVIEW,
        _build_user_prompt(title, answers),
        system=prompt.text,
        prompt_version=prompt.version,
    )
    body = generation.text.strip()
    if not body:
        raise RuntimeError(
            "Das Modell lieferte keine Zusammenfassung — Modell nicht verfügbar oder leere Antwort"
        )

    job_queue.update(status, progress=0.8, state=JobState.RUNNING)
    vault = open_vault()
    domain = vault.load_domain(domain_name)
    candidate = Entity(
        id=f"{domain.folder_for(entity_type)}/{_slugify(title)}",
        type=entity_type,
        title=title,
        domain=domain_name,
        owner=Owner.USER,
        confidence=INTERVIEW_CONFIDENCE,
        media_links=media_links,
        body=body,
    )
    validation_errors = validate_entity(candidate, domain)

    explainability: dict[str, Any] = {
        "model_id": generation.model_id,
        "capability": generation.capability,
        "prompt_version": generation.prompt_version,
        "duration_ms": generation.duration_ms,
        "confidence": INTERVIEW_CONFIDENCE,
        "reason": "Zusammengefasst aus deinen Interview-Antworten (keine Web-/Fremdquellen).",
    }

    if validation_errors:
        # Ungültiger Kandidat wird abgewiesen, nicht als Zusammenfassung gezeigt (AK Phase 4).
        result: dict[str, Any] = {
            "suggestion": None,
            "explainability": explainability,
            "validation_errors": validation_errors,
        }
        log.info("interview: Vorschlag für '%s' abgewiesen (%d Fehler)", title, len(validation_errors))
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
        log.info("interview: Zusammenfassung für '%s' erzeugt (%.0f ms)", title, generation.duration_ms)

    job_queue.set_result(status, result)


async def run_interview_job(
    status: JobStatus,
    title: str,
    domain_name: str,
    entity_type: str,
    media_links: MediaLinks,
    answers: list[InterviewAnswer],
) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_interview, status, title, domain_name, entity_type, media_links, answers)


async def enqueue_interview(
    title: str,
    domain_name: str,
    entity_type: str,
    answers: list[InterviewAnswer],
    media_links: MediaLinks | None = None,
) -> JobStatus:
    links = media_links or MediaLinks()

    async def _factory(status: JobStatus) -> None:
        await run_interview_job(status, title, domain_name, entity_type, links, answers)

    return await job_queue.enqueue(
        kind=JobKind.INTERVIEW,
        label=f"Interview: {title}",
        coro_factory=_factory,
    )
