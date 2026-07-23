"""KnowledgeDiscoveryJob (P38) — Websuche + Gemma schlägt Fakten für eine öffentliche Entity
vor. Schreibt NICHTS: das Ergebnis ist eine Vorschlagsliste, die der User im Wizard abhakt
(ADR-031). Der Schreibweg ist die Übernahme-Route in api/knowledge_ai.py.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from photofant.db.session import SessionLocal
from photofant.inference.capabilities import Capability, generate
from photofant.inference.prompt_library import PromptLibrary
from photofant.inference.web_search import WebSearchError, WebSearchResult, search_web
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.knowledge.domains import Domain
from photofant.knowledge.schema import Entity, Owner
from photofant.knowledge.service import EntityNotFoundError, KnowledgeService, PrivateDomainError
from photofant.knowledge.vault import open_vault

log = logging.getLogger(__name__)

_PROMPT_NAME = "knowledge_discovery"
MAX_SEARCH_RESULTS = 5

# Deckt, was der Prompt für "bereits gesetzte Merkmale" braucht — nur zur Anzeige im
# User-Prompt, keine Berechtigungsprüfung (die läuft in set_attributes, Phase 4).
_OWNER_HINTS: dict[Owner, str] = {
    Owner.USER: "von dir gesetzt",
    Owner.MANUAL: "manuell gepflegt",
    Owner.WEB: "aus Web-Recherche",
    Owner.INFERRED: "geschätzt",
}


@dataclass
class DiscoveredFact:
    field: str  # Merkmals-Key aus der Domäne, oder "body"
    label: str  # Anzeigename ("Beruf", "Beschreibung")
    value: str
    source: str  # Host der Quelle, z.B. "linkedin.com"
    source_url: str
    confidence: float


@dataclass
class DiscoveredEntity:
    title: str
    type: str
    relationship_type: str
    body: str


@dataclass
class DiscoveryOutput:
    facts: list[DiscoveredFact]
    new_entities: list[DiscoveredEntity]
    sources: list[str]
    # Parser-Hinweise ("3 Zeilen im Abschnitt FAKTEN konnten nicht gelesen werden") —
    # kosmetisch, keine Schreibfehler, wandern unverändert in `JobDto.result.errors`.
    errors: list[str] = field(default_factory=list)


def _split_sections(raw: str) -> dict[str, str]:
    """Zerlegt den Modell-Output an den ### MARKER-Zeilen. Unbekannte Marker werden
    ignoriert, Text vor dem ersten Marker verworfen."""
    sections = {"FAKTEN": "", "NEUE_ENTITAETEN": "", "QUELLEN": ""}
    current: str | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        marker = next((name for name in sections if stripped == f"### {name}"), None)
        if marker is not None:
            current = marker
            continue
        if current is not None:
            sections[current] += line + "\n"
    return sections


def _parse_pipe_line(line: str) -> dict[str, str]:
    """`- Feld: X | Wert: Y` → `{"Feld": "X", "Wert": "Y"}`. Segmente ohne Doppelpunkt
    werden verworfen — das ist der Normalfall bei leicht danebenliegendem Modell-Output."""
    cleaned = line.strip().lstrip("-*").strip()
    parts: dict[str, str] = {}
    for segment in cleaned.split("|"):
        if ":" not in segment:
            continue
        key, _, value = segment.partition(":")
        parts[key.strip()] = value.strip()
    return parts


def _candidate_lines(section_text: str) -> list[str]:
    """Nicht-leere Zeilen einer Sektion, ohne das Leer-Sentinel "keine"."""
    return [
        line.strip()
        for line in section_text.splitlines()
        if line.strip() and line.strip().lower() != "keine"
    ]


def _fact_from_parts(parts: dict[str, str], field_labels: dict[str, str]) -> DiscoveredFact | None:
    feld = parts.get("Feld", "").strip()
    if not feld:
        log.warning("Discovery-Parser: FAKTEN-Zeile ohne 'Feld' verworfen: %r", parts)
        return None
    if feld == "beschreibung":
        field_key, label = "body", "Beschreibung"
    elif feld in field_labels:
        field_key, label = feld, field_labels[feld]
    else:
        log.warning("Discovery-Parser: unbekanntes Feld '%s' verworfen", feld)
        return None

    wert = parts.get("Wert", "").strip()
    if not wert:
        log.warning("Discovery-Parser: FAKTEN-Zeile ohne 'Wert' verworfen: %r", parts)
        return None

    quelle = parts.get("Quelle", "").strip()
    source_url = ""
    source = "—"
    if quelle:
        parsed_url = urlparse(quelle)
        if parsed_url.scheme and parsed_url.netloc:
            source_url = quelle
            netloc = parsed_url.netloc
            source = netloc[4:] if netloc.startswith("www.") else netloc

    try:
        confidence = float(parts.get("Konfidenz", ""))
    except ValueError:
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return DiscoveredFact(
        field=field_key, label=label, value=wert, source=source, source_url=source_url, confidence=confidence
    )


def _entity_from_parts(parts: dict[str, str]) -> DiscoveredEntity | None:
    titel = parts.get("Titel", "").strip()
    typ = parts.get("Typ", "").strip()
    beziehung = parts.get("Beziehung", "").strip()
    if not titel or not typ or not beziehung:
        log.warning("Discovery-Parser: NEUE_ENTITAETEN-Zeile unvollständig verworfen: %r", parts)
        return None
    return DiscoveredEntity(
        title=titel, type=typ, relationship_type=beziehung, body=parts.get("Info", "").strip()
    )


def _parse_discovery_output(raw: str, field_labels: dict[str, str]) -> DiscoveryOutput:
    """Defensiver Parser für das 3-Sektionen-Format aus dem Prompt (Phase 1).

    Fehlt eine Sektion oder ist sie leer/„keine" → leeres Ergebnis für genau diese
    Sektion, kein Fehler. Ein komplett unparsbarer Output liefert ein volles
    Leer-Ergebnis — der Wizard zeigt dann „Nichts gefunden", statt zu crashen.

    ``field_labels`` bildet Merkmals-Key → Anzeigename ab (aus ``Domain.fields_for``),
    plus den Sonderfall ``"beschreibung" → "Beschreibung"``.
    """
    sections = _split_sections(raw)
    errors: list[str] = []

    fakten_lines = _candidate_lines(sections["FAKTEN"])
    facts = [
        fact
        for fact in (_fact_from_parts(_parse_pipe_line(line), field_labels) for line in fakten_lines)
        if fact is not None
    ]
    dropped_facts = len(fakten_lines) - len(facts)
    if dropped_facts:
        errors.append(f"{dropped_facts} Zeile(n) im Abschnitt FAKTEN konnten nicht gelesen werden")

    entity_lines = _candidate_lines(sections["NEUE_ENTITAETEN"])
    new_entities = [
        entity
        for entity in (_entity_from_parts(_parse_pipe_line(line)) for line in entity_lines)
        if entity is not None
    ]
    dropped_entities = len(entity_lines) - len(new_entities)
    if dropped_entities:
        errors.append(
            f"{dropped_entities} Zeile(n) im Abschnitt NEUE_ENTITAETEN konnten nicht gelesen werden"
        )

    sources = [line for line in sections["QUELLEN"].splitlines() if line.strip().startswith("http")]

    return DiscoveryOutput(facts=facts, new_entities=new_entities, sources=sources, errors=errors)


def _field_labels_for(domain: Domain, type_name: str) -> dict[str, str]:
    labels = {field_def.key: field_def.label for field_def in domain.fields_for(type_name)}
    labels["beschreibung"] = "Beschreibung"
    return labels


def _build_user_prompt(entity: Entity, domain: Domain, results: list[WebSearchResult]) -> str:
    aliases = ", ".join(entity.aliases) if entity.aliases else "keine"
    relationships = (
        ", ".join(f"{relationship.type}→{relationship.target}" for relationship in entity.relationships)
        if entity.relationships
        else "keine"
    )

    field_defs = domain.fields_for(entity.type)
    allowed_fields = (
        ", ".join(f"{field_def.key} ({field_def.label})" for field_def in field_defs)
        if field_defs
        else "nur beschreibung"
    )

    existing_attributes = (
        "\n".join(
            f"- {key} = {attribute.value} ({_OWNER_HINTS[attribute.owner]})"
            for key, attribute in entity.attributes.items()
        )
        if entity.attributes
        else "keine"
    )

    allowed_types = ", ".join(sorted(domain.entity_types)) or "keine"
    allowed_relationships = ", ".join(sorted(domain.relationship_types)) or "keine"

    results_block = (
        "\n".join(
            f"[{index}] {result.title} / {result.url} / {result.snippet}"
            for index, result in enumerate(results, start=1)
        )
        if results
        else "(keine Suchergebnisse)"
    )

    return (
        f"Entity-Titel: {entity.title}\n"
        f"Typ: {entity.type}\n"
        f"Domäne: {entity.domain}\n"
        f"Aliase: {aliases}\n\n"
        f"Erlaubte Merkmals-Keys (plus 'beschreibung', das ist immer erlaubt): {allowed_fields}\n\n"
        f"Bereits gesetzte Merkmale (schlage diese nicht erneut vor):\n{existing_attributes}\n\n"
        f"Aktuelle Beschreibung:\n{entity.body or '(leer)'}\n\n"
        f"Bestehende Beziehungen: {relationships}\n\n"
        f"Erlaubte Entity-Typen der Domäne: {allowed_types}\n"
        f"Erlaubte Beziehungstypen der Domäne: {allowed_relationships}\n\n"
        f"Suchergebnisse:\n{results_block}\n\n"
        "Nenne nur Fakten, die durch die Snippets gedeckt sind."
    )


def _fact_to_dict(fact: DiscoveredFact) -> dict[str, Any]:
    return {
        "field": fact.field,
        "label": fact.label,
        "value": fact.value,
        "source": fact.source,
        "source_url": fact.source_url,
        "confidence": fact.confidence,
    }


def _entity_to_dict(entity: DiscoveredEntity) -> dict[str, Any]:
    return {
        "title": entity.title,
        "type": entity.type,
        "relationship_type": entity.relationship_type,
        "body": entity.body,
    }


def _build_queries(entity: Entity, hint: str | None, preferred: tuple[str, ...]) -> list[str]:
    """Baut die Suchanfrage(n) für *entity*. Ohne bevorzugte Quellen exakt eine Anfrage
    (unverändertes Verhalten); mit bevorzugten Quellen zusätzlich davor eine auf sie
    eingeschränkte Anfrage (`site:` mit `OR` verknüpft — verifiziert gegen `ddgs`)."""
    base = f"{entity.title} {entity.type}"
    if hint is not None and hint.strip():
        base = f"{base} {hint.strip()}"
    if not preferred:
        return [base]
    site_filter = " OR ".join(f"site:{source}" for source in preferred)
    return [f"{base} ({site_filter})", base]


def _merge_results(
    primary: list[WebSearchResult], fallback: list[WebSearchResult], limit: int
) -> list[WebSearchResult]:
    """Führt *primary* (bevorzugte Quellen) vor *fallback* (offene Suche) zusammen,
    entdoppelt nach URL unter Beibehaltung der Reihenfolge, kürzt auf *limit*."""
    merged: list[WebSearchResult] = []
    seen_urls: set[str] = set()
    for result in (*primary, *fallback):
        if result.url in seen_urls:
            continue
        seen_urls.add(result.url)
        merged.append(result)
        if len(merged) >= limit:
            break
    return merged


def _run_discovery(status: JobStatus, entity_id: str, hint: str | None = None) -> None:
    prompt = PromptLibrary().get(_PROMPT_NAME)
    if prompt is None:
        raise RuntimeError(
            f"Prompt '{_PROMPT_NAME}' nicht gefunden — Prompt-Library prüfen (ai.promptLibraryPath)"
        )

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    vault = open_vault()
    with SessionLocal() as session:
        service = KnowledgeService(session, vault)
        entity = service.find_entity(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"Entity '{entity_id}' nicht gefunden")
        domain = vault.load_domain(entity.domain)
        if domain.private:
            raise PrivateDomainError(
                f"Domäne '{entity.domain}' ist privat — keine Web-Recherche (Konzept-ADR-009)"
            )
    # Session bewusst geschlossen — der Job hält keine Schreib-Session über Suche +
    # Modell-Call, beide können mehrere Sekunden dauern.

    job_queue.update(status, progress=0.3, state=JobState.RUNNING)
    # Optionaler Hinweis aus dem Web-Suche-Wizard (Beruf, Stadt, Link …) — hilft bei
    # Namensvettern, hat aber keinen eigenen Kontrakt-Slot im Prompt, nur in der Suchanfrage.
    preferred_sources = domain.preferred_sources_for(entity.type)
    queries = _build_queries(entity, hint, preferred_sources)
    if len(queries) == 1:
        try:
            results = search_web(queries[0], max_results=MAX_SEARCH_RESULTS)
        except WebSearchError as error:
            raise RuntimeError(str(error)) from error
    else:
        restricted_query, open_query = queries
        try:
            restricted_results = search_web(restricted_query, max_results=MAX_SEARCH_RESULTS)
        except WebSearchError:
            # Ein zu enger site:-Filter darf die Recherche nicht scheitern lassen —
            # der offene Durchlauf trägt (AK Teil A #4).
            restricted_results = []
        try:
            open_results = search_web(open_query, max_results=MAX_SEARCH_RESULTS)
        except WebSearchError as error:
            raise RuntimeError(str(error)) from error
        results = _merge_results(restricted_results, open_results, MAX_SEARCH_RESULTS)

    field_labels = _field_labels_for(domain, entity.type)
    user_prompt = _build_user_prompt(entity, domain, results)

    job_queue.update(status, progress=0.5, state=JobState.RUNNING)
    generation = generate(
        Capability.KNOWLEDGE_DISCOVERY,
        user_prompt,
        system=prompt.text,
        prompt_version=prompt.version,
        max_new_tokens=768,
    )
    if not generation.text.strip():
        raise RuntimeError("Das Modell lieferte keine Antwort — Modell nicht verfügbar oder leere Antwort")

    output = _parse_discovery_output(generation.text, field_labels)
    job_queue.update(status, progress=0.9, state=JobState.RUNNING)

    explainability: dict[str, Any] = {
        "model_id": generation.model_id,
        "capability": generation.capability,
        "prompt_version": generation.prompt_version,
        "duration_ms": generation.duration_ms,
        "confidence": None,
        "reason": "Web-Recherche — Vorschläge, nichts wurde geschrieben.",
    }

    result: dict[str, Any] = {
        "facts": [_fact_to_dict(fact) for fact in output.facts],
        "entity_suggestions": [_entity_to_dict(entity_suggestion) for entity_suggestion in output.new_entities],
        "sources": output.sources,
        "errors": output.errors,
        "explainability": explainability,
    }
    log.info(
        "knowledge_discovery: '%s' → %d Fakten, %d neue Entitäten, %d Quellen (%.0f ms)",
        entity_id,
        len(output.facts),
        len(output.new_entities),
        len(output.sources),
        generation.duration_ms,
    )
    job_queue.set_result(status, result)


async def run_knowledge_discovery_job(status: JobStatus, entity_id: str, hint: str | None = None) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_discovery, status, entity_id, hint)


async def enqueue_knowledge_discovery(entity_id: str, hint: str | None = None) -> JobStatus:
    async def _factory(status: JobStatus) -> None:
        await run_knowledge_discovery_job(status, entity_id, hint)

    return await job_queue.enqueue(
        kind=JobKind.KNOWLEDGE_DISCOVERY,
        label=f"Web-Recherche: {entity_id}",
        coro_factory=_factory,
    )
