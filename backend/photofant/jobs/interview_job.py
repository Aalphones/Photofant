"""InterviewJob (P27 Phase 4, erweitert in P39 Phase 2) — ein geführter Interview-Dialog
über eine PRIVATE Person/ein Haustier wird zu einem Entity-Vorschlag.

Der Nutzer beantwortet im Wizard drei Erzähl-Fragen und — je Merkmal des Typs, das in der
Domäne eine ``question`` trägt — ein eigenes kurzes Eingabefeld (alles optional). Nach der
letzten Antwort läuft dieser Job **einmal**: er fordert die Fähigkeit ``INTERVIEW`` an (nie
ein Modell — ADR-027) und lässt Gemma aus den Erzähl-Antworten einen Beschreibungsabsatz
**synthetisieren**. Der Kandidat wird gegen die Domäne geprüft (P22-Validator).

Zwei Wege füllen die Merkmale, mit klarer Gewichtung (ADR-034):

* **Gefragt** — was der Nutzer selbst eingetippt hat, wird wörtlich übernommen (Owner
  ``user``, volle Confidence). Kein Modell dazwischen, keine Halluzination möglich.
* **Geschätzt** — nur für Merkmale, die der Nutzer **leer gelassen** hat, darf Gemma aus den
  Erzähl-Antworten einen Wert vorschlagen (Owner ``inferred``, als KI-Schätzung erkennbar).

Das präzisiert Konzept-ADR-009 („nur zusammenfassen, nie Fakten erfinden"), hebt es aber
nicht auf: ein selbst eingetippter Wert ist kein erfundener Fakt, und der Modell-Pfad bleibt
optional, auf leere Felder beschränkt und markiert. Bricht das JSON-Parsen, überleben die
gefragten Merkmale trotzdem — sie hängen nicht am Modell.

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
import json
import logging
import re
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from typing import Any

from photofant.inference.capabilities import Capability, generate
from photofant.inference.prompt_library import PromptLibrary
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.knowledge.domains import FieldDef
from photofant.knowledge.schema import Attribute, Entity, MediaLinks, Owner
from photofant.knowledge.validator import validate_entity
from photofant.knowledge.vault import open_vault

log = logging.getLogger(__name__)

# Die Fakten stammen direkt vom Nutzer (er hat sie im Interview genannt), nicht aus
# einer Modell-Inferenz — anders als beim Import-/Update-Vorschlag. Der Kandidat trägt
# deshalb volle Confidence; bestätigt wird er trotzdem manuell (Sicherheitsregel).
INTERVIEW_CONFIDENCE = 1.0

# Confidence für eine Modell-Schätzung, die keine eigene mitliefert — bewusst mittig:
# die Anzeige soll sie klar unter einem gefragten Wert einsortieren, ohne sie zu verwerfen.
INFERRED_FALLBACK_CONFIDENCE = 0.5

_PROMPT_NAME = "interview"

_CODE_FENCE_START = re.compile(r"^```[a-zA-Z]*\s*")
_CODE_FENCE_END = re.compile(r"\s*```$")


@dataclass(frozen=True)
class InterviewAnswer:
    """Ein beantwortetes Interview-Frage-Paar aus dem geführten Dialog.

    ``field_key`` ist gesetzt, wenn die Antwort zu einem Merkmal des Entity-Typs gehört
    (Schritt „Eckdaten" im Wizard) — dieser Wert wird wörtlich übernommen. Erzähl-Antworten
    tragen kein ``field_key``; sie speisen nur den Beschreibungsabsatz.
    """

    question: str
    answer: str
    field_key: str | None = None


def _slugify(value: str) -> str:
    """Baut aus dem Titel einen id-Slug (nur fürs Validieren des Kandidaten — der Wizard
    baut die endgültige id beim Speichern selbst neu, dieser Wert erreicht den Vault nie)."""
    lowered = value.strip().lower()
    ascii_only = lowered.encode("ascii", "ignore").decode("ascii")
    hyphenated = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return hyphenated or "person"


def _split_answers(
    answers: Iterable[InterviewAnswer], known_keys: Collection[str]
) -> tuple[list[InterviewAnswer], dict[str, str]]:
    """Trennt Erzähl-Antworten von den gefragten Merkmalen.

    Ein ``field_key``, den die Domäne nicht kennt, wird verworfen statt durchgereicht —
    die Merkmals-Keys einer Entity kommen ausschließlich aus der Domänen-Datei.
    """
    narrative: list[InterviewAnswer] = []
    answered_fields: dict[str, str] = {}
    for answer in answers:
        if answer.field_key is None:
            narrative.append(answer)
            continue
        if answer.field_key not in known_keys:
            log.debug("interview: unbekannter field_key '%s' verworfen", answer.field_key)
            continue
        value = answer.answer.strip()
        if value:
            answered_fields[answer.field_key] = value
    return narrative, answered_fields


def _build_user_prompt(
    title: str, narrative: list[InterviewAnswer], open_fields: tuple[FieldDef, ...]
) -> str:
    """Der Kontext-Turn für Gemma: die Erzähl-Antworten als Protokoll, dazu die Merkmale,
    die der Nutzer leer gelassen hat. Die Rollen-/Regelanweisung (nur zusammenfassen, nie
    erfinden, kein Web) kommt als System-Teil aus der Prompt-Library; hier nur der
    konkrete Fall."""
    transcript = "\n".join(
        f"Frage: {answer.question}\nAntwort: {answer.answer.strip()}"
        for answer in narrative
        if answer.answer.strip()
    )
    parts = [
        f"Name: {title}",
        "",
        "Interview-Antworten:",
        transcript or "(keine Antworten)",
    ]
    if open_fields:
        listing = "\n".join(
            f"- {field_def.key} ({field_def.label})" for field_def in open_fields
        )
        parts += ["", "Noch offene Merkmale (nur diese Keys sind erlaubt):", listing]
    parts += ["", "Antworte als JSON wie in den Regeln beschrieben."]
    return "\n".join(parts)


def _strip_code_fence(raw: str) -> str:
    """Entfernt einen umschließenden Markdown-Code-Block (```json … ```)."""
    stripped = raw.strip()
    if not stripped.startswith("```"):
        return stripped
    without_opening = _CODE_FENCE_START.sub("", stripped)
    return _CODE_FENCE_END.sub("", without_opening).strip()


def _clamp_confidence(raw: Any) -> float:
    """Confidence aus dem Modell-JSON auf ``0.0..1.0`` klemmen; fehlend/ungültig → Fallback."""
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        return INFERRED_FALLBACK_CONFIDENCE
    return max(0.0, min(1.0, float(raw)))


def _parse_suggested_attributes(raw: Any, allowed: Collection[str]) -> dict[str, Attribute]:
    """Die vom Modell vorgeschlagenen Merkmale, hart gefiltert.

    Alles, was nicht in ``allowed`` steht (= Merkmal der Domäne, vom Nutzer leer gelassen),
    fliegt raus — das Modell darf die Merkmals-Liste nicht erweitern.
    """
    if not isinstance(raw, dict):
        return {}

    attributes: dict[str, Attribute] = {}
    for key, entry in raw.items():
        if key not in allowed:
            continue
        value = entry.get("value") if isinstance(entry, dict) else entry
        if not isinstance(value, str) or not value.strip():
            continue
        confidence = entry.get("confidence") if isinstance(entry, dict) else None
        attributes[key] = Attribute(
            value=value.strip(),
            owner=Owner.INFERRED,
            confidence=_clamp_confidence(confidence),
        )
    return attributes


def _parse_interview_output(raw: str, allowed: Collection[str]) -> tuple[str, dict[str, Attribute]]:
    """Zerlegt die Modell-Antwort in Beschreibungsabsatz und geschätzte Merkmale.

    JSON aus einem rohen Text-LM ist nicht garantiert. Scheitert das Parsen, ist das **kein**
    Fehlerfall: der komplette Text wird zum Absatz, und die Merkmale bleiben leer — die
    gefragten Merkmale kommen ohnehin nicht von hier (AK 7).
    """
    fallback: tuple[str, dict[str, Attribute]] = (raw.strip(), {})
    try:
        parsed: Any = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError:
        log.info("interview: Modell lieferte kein gültiges JSON — Text wird als Absatz übernommen")
        return fallback

    if not isinstance(parsed, dict):
        return fallback
    body = parsed.get("body")
    if not isinstance(body, str) or not body.strip():
        return fallback

    return body.strip(), _parse_suggested_attributes(parsed.get("attributes"), allowed)


def _merge_attributes(
    answered_fields: dict[str, str], suggested: dict[str, Attribute]
) -> dict[str, Attribute]:
    """Gefragte Merkmale zuerst — ein Modell-Vorschlag füllt nur, was noch leer ist (AK 6)."""
    merged: dict[str, Attribute] = {
        key: Attribute(value=value, owner=Owner.USER, confidence=INTERVIEW_CONFIDENCE)
        for key, value in answered_fields.items()
    }
    for key, attribute in suggested.items():
        if key not in merged:
            merged[key] = attribute
    return merged


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

    # Die Domäne wird **vor** dem Modell-Aufruf gebraucht: sie liefert die erlaubten
    # Merkmals-Keys, und die gehen als „noch offen"-Liste in den Prompt.
    vault = open_vault()
    domain = vault.load_domain(domain_name)
    field_defs = domain.fields_for(entity_type)
    labels = {field_def.key: field_def.label for field_def in field_defs}

    narrative, answered_fields = _split_answers(answers, labels.keys())
    open_fields = tuple(field_def for field_def in field_defs if field_def.key not in answered_fields)

    job_queue.update(status, progress=0.3, state=JobState.RUNNING)
    generation = generate(
        Capability.INTERVIEW,
        _build_user_prompt(title, narrative, open_fields),
        system=prompt.text,
        prompt_version=prompt.version,
    )
    raw_output = generation.text.strip()
    if not raw_output:
        raise RuntimeError(
            "Das Modell lieferte keine Zusammenfassung — Modell nicht verfügbar oder leere Antwort"
        )

    job_queue.update(status, progress=0.8, state=JobState.RUNNING)
    body, suggested = _parse_interview_output(
        raw_output, {field_def.key for field_def in open_fields}
    )
    attributes = _merge_attributes(answered_fields, suggested)

    candidate = Entity(
        id=f"{domain.folder_for(entity_type)}/{_slugify(title)}",
        type=entity_type,
        title=title,
        domain=domain_name,
        owner=Owner.USER,
        confidence=INTERVIEW_CONFIDENCE,
        media_links=media_links,
        attributes=attributes,
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
                # Das Label reist mit, damit der Wizard die Merkmale ohne eigene
                # Domänen-Auflösung anzeigen kann (Kontrakt 1 des Plans).
                "attributes": {
                    key: {
                        "label": labels.get(key, key),
                        "value": attribute.value,
                        "owner": attribute.owner.value,
                        "confidence": attribute.confidence,
                    }
                    for key, attribute in attributes.items()
                },
            },
            "explainability": explainability,
            "validation_errors": [],
        }
        log.info(
            "interview: Zusammenfassung für '%s' erzeugt (%d Merkmale, %.0f ms)",
            title,
            len(attributes),
            generation.duration_ms,
        )

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
