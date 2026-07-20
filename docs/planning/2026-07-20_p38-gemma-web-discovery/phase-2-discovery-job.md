# Phase 2 — KnowledgeDiscoveryJob (Suche → Gemma → Auto-Write)

**Komplexität:** heikel (neuer Schreibpfad ohne Bestätigung, Parsing von Freitext-Output).
**Voraussetzung:** Phase 1 abgeschlossen (Capability, Prompt, `search_web()` verifiziert).

## Kontext (lesen vor dem Start)
- `backend/photofant/jobs/knowledge_update_job.py` — Struktur-Vorbild (Prompt laden, Job-
  Progress-Schritte, `generate()`-Aufruf, `job_queue.set_result`).
- `backend/photofant/jobs/knowledge_patch_job.py` — Vorbild für „direkt schreiben +
  Changelog + Recommendation-Invalidierung" (`_run_patch`, Zeile ~38-70).
- `backend/photofant/knowledge/service.py` — `create_entity(entity, owner)` (Zeile 104),
  `update_entity(entity_id, patch, owner)` (152), `validate_patch(entity_id, patch)` (168),
  `create_relationship(entity_id, relationship, owner)` (188), `find_entity` (132),
  `search_entities` (146). Alle bereits ownership- und domain-validiert — kein Extra-Guard
  in diesem Job nötig außer dem Privat-Domain-Check (Aufgabe 2 unten).
- `backend/photofant/knowledge/schema.py` — `Entity`, `Relationship`, `Owner.WEB`,
  `owner_can_overwrite`.
- `backend/photofant/knowledge/domains.py` — `Domain.has_entity_type`,
  `Domain.has_relationship_type`, `Domain.folder_for(type_name)` (Zeile 47, wirft
  `DomainLoadError` bei unbekanntem Typ — abfangen, nicht durchreichen).
- `backend/photofant/knowledge/changelog.py` — `ChangelogService.record(entity_id, field,
  old_value, new_value, reason, source, job_id)`.
- `backend/photofant/jobs/recommendation_job.py` — `invalidate_recommendations(session,
  asset_ids)` — nur relevant, wenn neue Beziehungen entstehen (wie in `knowledge_patch_job.py`
  vorgemacht).
- `backend/photofant/inference/web_search.py` (Phase 1) — `search_web`, `WebSearchResult`,
  `WebSearchError`.
- `frontend/src/app/features/wissen/entity-wizard-dialog/entity-wizard-dialog.ts` Zeile
  278-285 — die `slugify()`-Referenzimplementierung (Backend braucht ein Python-Äquivalent,
  siehe Aufgabe 3).
- `backend/photofant/knowledge/domains/movies.yaml` — Beispiel-Domäne: `entity_types`
  (Actor/Movie/Location/…), `relationship_types` (`appears_in`, `located_in`, …) — die Werte,
  die Gemma im Prompt als „erlaubte Typen/Beziehungen" vorgelegt bekommt.

## Aufgabe 1 — Slugify-Helper (Backend, existiert noch nicht)
Neue kleine Funktion in `backend/photofant/knowledge/service.py` (oder eigenes Modul
`knowledge/slug.py`, falls der Datei-Stil im Projekt kleine Utility-Module bevorzugt — ein
eigenes Modul ist hier sauberer, da `service.py` bereits groß ist):

```python
# backend/photofant/knowledge/slug.py
"""Slug-Erzeugung für backend-seitig (nicht vom User im Wizard) erzeugte Entity-IDs.

Spiegelt exakt die Frontend-Logik (entity-wizard-dialog.ts::slugify) — gleiche Regel,
zwei Sprachen, damit IDs unabhängig vom Entstehungsweg gleich aussehen.
"""
from __future__ import annotations

import re
import unicodedata


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    without_diacritics = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "-", without_diacritics.strip())
    return slug.strip("-")
```

## Aufgabe 2 — Output-Parser
Neue Funktion in `jobs/knowledge_discovery_job.py` (siehe Aufgabe 3 für die Datei als Ganzes):

```python
@dataclass
class DiscoveredEntity:
    title: str
    type: str
    relationship_type: str
    body: str


@dataclass
class DiscoveryOutput:
    body: str | None
    new_entities: list[DiscoveredEntity]
    sources: list[str]


def _parse_discovery_output(raw: str) -> DiscoveryOutput:
    """Defensiver Parser für das feste 3-Sektionen-Format aus dem Prompt (Phase 1).
    Fehlt eine Sektion oder ist sie leer/„keine" → leeres Ergebnis für genau diese
    Sektion, kein Fehler. Ein komplett unparsbarer Output (keine Marker gefunden)
    liefert ein volles Leer-Ergebnis — der Job schreibt dann nichts, statt zu crashen."""
    sections = {"BESCHREIBUNG": "", "NEUE_ENTITAETEN": "", "QUELLEN": ""}
    current: str | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        marker = next((name for name in sections if stripped == f"### {name}"), None)
        if marker is not None:
            current = marker
            continue
        if current is not None:
            sections[current] += line + "\n"

    body = sections["BESCHREIBUNG"].strip() or None

    new_entities: list[DiscoveredEntity] = []
    for line in sections["NEUE_ENTITAETEN"].strip().splitlines():
        line = line.strip().lstrip("-").strip()
        if not line or line.lower() == "keine":
            continue
        parts = dict(
            (segment.split(":", 1)[0].strip(), segment.split(":", 1)[1].strip())
            for segment in line.split("|")
            if ":" in segment
        )
        title, type_, relationship = parts.get("Titel"), parts.get("Typ"), parts.get("Beziehung")
        if not title or not type_ or not relationship:
            log.warning("knowledge_discovery: Zeile nicht parsbar, übersprungen: %r", line)
            continue
        new_entities.append(
            DiscoveredEntity(title=title, type=type_, relationship_type=relationship, body=parts.get("Info", ""))
        )

    sources = [line.strip() for line in sections["QUELLEN"].strip().splitlines() if line.strip()]

    return DiscoveryOutput(body=body, new_entities=new_entities, sources=sources)
```

**Parser-Test (Konfidenz-Ausweis README, vor Phase 3/4):** nach der ersten echten
Generierung (`_run_discovery` unten, manuell gegen 5-10 reale, bekannte öffentliche Personen
laufen lassen) die Trefferquote protokollieren: Wie oft liefert Gemma das exakte
`### MARKER`-Format? Bei niedriger Trefferquote (grob: unter der Hälfte) den Prompt in
Phase 1 nachschärfen (z.B. ein Beispiel-Output ins Prompt aufnehmen), bevor Phase 3/4
draufbauen — nicht den Parser komplizierter machen, das Modell steuern.

## Aufgabe 3 — Der Job
Neue Datei `backend/photofant/jobs/knowledge_discovery_job.py`:

```python
"""KnowledgeDiscoveryJob (P38) — Websuche + Gemma erweitert eine öffentliche Entity und
schlägt neue verknüpfte Entitäten vor. Schreibt DIREKT (owner=web), keine Bestätigung
(ADR-031 — bewusste Ausnahme von der P27-Kernregel). Löst keine Folge-Jobs aus außer der
Recommendation-Invalidierung bei neuen Beziehungen (wie KnowledgePatchJob).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from photofant.db.session import SessionLocal
from photofant.inference.capabilities import Capability, generate
from photofant.inference.prompt_library import PromptLibrary
from photofant.inference.web_search import WebSearchError, WebSearchResult, search_web
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.jobs.recommendation_job import invalidate_recommendations
from photofant.knowledge.changelog import ChangelogService
from photofant.knowledge.domains import Domain
from photofant.knowledge.schema import Entity, Owner, Relationship
from photofant.knowledge.service import EntityAlreadyExistsError, EntityNotFoundError, KnowledgeService
from photofant.knowledge.slug import slugify
from photofant.knowledge.validator import ValidationError
from photofant.knowledge.vault import open_vault
from photofant.recommendation.context import assets_for_entity

log = logging.getLogger(__name__)

MAX_SEARCH_RESULTS = 5
_PROMPT_NAME = "knowledge_discovery"


class PrivateDomainError(RuntimeError):
    """Verteidigung in der Tiefe — die API-Route (Phase 3) blockt das schon vorher."""


def _build_user_prompt(entity: Entity, domain: Domain, results: list[WebSearchResult]) -> str:
    aliases = ", ".join(entity.aliases) if entity.aliases else "keine"
    relationships = (
        ", ".join(f"{r.type}→{r.target}" for r in entity.relationships) if entity.relationships else "keine"
    )
    result_block = "\n\n".join(
        f"[{i+1}] {r.title}\nURL: {r.url}\n{r.snippet}" for i, r in enumerate(results)
    ) or "(keine Suchergebnisse)"
    allowed_types = ", ".join(sorted(domain.entity_types.keys()))
    allowed_relationships = ", ".join(sorted(domain.relationship_types))
    return (
        f"Entity-Titel: {entity.title}\n"
        f"Typ: {entity.type}\n"
        f"Domäne: {entity.domain}\n"
        f"Aliase: {aliases}\n"
        f"Bestehende Beziehungen: {relationships}\n"
        f"Aktuelle Beschreibung:\n{entity.body or '(leer)'}\n\n"
        f"Erlaubte Entity-Typen in dieser Domäne: {allowed_types}\n"
        f"Erlaubte Beziehungstypen in dieser Domäne: {allowed_relationships}\n\n"
        f"Web-Suchergebnisse:\n{result_block}\n\n"
        "Erweitere die Beschreibung und schlage neue verknüpfte Entitäten vor, ausschließlich "
        "im vorgegebenen Format."
    )


def _run_discovery(status: JobStatus, entity_id: str) -> None:
    prompt = PromptLibrary().get(_PROMPT_NAME)
    if prompt is None:
        raise RuntimeError(f"Prompt '{_PROMPT_NAME}' nicht gefunden — Prompt-Library prüfen")

    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    vault = open_vault()
    with SessionLocal() as session:
        service = KnowledgeService(session, vault)
        entity = service.find_entity(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"Entity '{entity_id}' nicht gefunden")

        domain = vault.load_domain(entity.domain)
        if domain.private:
            raise PrivateDomainError("Web-Discovery ist für private Domänen gesperrt (ADR-009/ADR-031)")

        job_queue.update(status, progress=0.2, state=JobState.RUNNING)
        try:
            results = search_web(f"{entity.title} {entity.type}", max_results=MAX_SEARCH_RESULTS)
        except WebSearchError as error:
            raise RuntimeError(str(error)) from error

        job_queue.update(status, progress=0.4, state=JobState.RUNNING)
        generation = generate(
            Capability.KNOWLEDGE_DISCOVERY,
            _build_user_prompt(entity, domain, results),
            system=prompt.text,
            prompt_version=prompt.version,
            max_new_tokens=768,
        )
        if not generation.text.strip():
            raise RuntimeError("Das Modell lieferte keine Antwort — Modell nicht verfügbar oder leere Antwort")

        parsed = _parse_discovery_output(generation.text)

        job_queue.update(status, progress=0.6, state=JobState.RUNNING)
        written_fields: list[str] = []
        created_entities: list[dict[str, str]] = []
        job_errors: list[str] = []
        touched_asset_ids: set[int] = set()

        if parsed.body:
            merged_sources = sorted(set(entity.sources) | set(parsed.sources))
            patch = {"body": parsed.body, "sources": merged_sources}
            validation_errors = service.validate_patch(entity_id, patch)
            if validation_errors:
                job_errors.extend(validation_errors)
            else:
                old_body = entity.body
                service.update_entity(entity_id, patch, Owner.WEB)
                ChangelogService(session).record(
                    entity_id=entity_id,
                    field="body",
                    old_value=old_body,
                    new_value=parsed.body,
                    reason="Web-Recherche (automatisch, Gemma, ohne Bestätigung — ADR-031)",
                    source=Owner.WEB.value,
                    job_id=status.id,
                )
                written_fields.append("body")

        for candidate in parsed.new_entities:
            if not domain.has_entity_type(candidate.type) or not domain.has_relationship_type(
                candidate.relationship_type
            ):
                job_errors.append(f"'{candidate.title}': unbekannter Typ oder Beziehung, übersprungen")
                continue

            existing = service.search_entities(candidate.title, type=candidate.type, domain=entity.domain)
            match = next(
                (e for e in existing if e.title.strip().lower() == candidate.title.strip().lower()), None
            )
            if match is None:
                new_entity = Entity(
                    id=f"{domain.folder_for(candidate.type)}/{slugify(candidate.title)}",
                    type=candidate.type,
                    title=candidate.title,
                    domain=entity.domain,
                    sources=list(parsed.sources),
                    body=candidate.body,
                )
                try:
                    created = service.create_entity(new_entity, Owner.WEB)
                except (EntityAlreadyExistsError, ValidationError) as error:
                    job_errors.append(f"'{candidate.title}': {error}")
                    continue
                created_entities.append({"id": created.id, "title": created.title, "type": created.type})
                target_id = created.id
            else:
                target_id = match.id

            already_linked = any(
                r.target == target_id and r.type == candidate.relationship_type for r in entity.relationships
            )
            if not already_linked:
                try:
                    service.create_relationship(
                        entity_id, Relationship(type=candidate.relationship_type, target=target_id), Owner.WEB
                    )
                    touched_asset_ids |= assets_for_entity(session, entity_id)
                    touched_asset_ids |= assets_for_entity(session, target_id)
                except ValidationError as error:
                    job_errors.append(f"Beziehung zu '{candidate.title}': {error}")

        if touched_asset_ids:
            invalidate_recommendations(session, touched_asset_ids)

        session.commit()

    explainability = {
        "model_id": generation.model_id,
        "capability": generation.capability,
        "prompt_version": generation.prompt_version,
        "duration_ms": generation.duration_ms,
        "confidence": None,
        "reason": "Web-Recherche, automatisch geschrieben (ADR-031) — keine Bestätigung nötig.",
    }
    job_queue.set_result(
        status,
        {
            "written_fields": written_fields,
            "created_entities": created_entities,
            "sources": parsed.sources,
            "errors": job_errors,
            "explainability": explainability,
        },
    )
    log.info(
        "knowledge_discovery: '%s' — %d Felder geschrieben, %d neue Entitäten, %d Fehler",
        entity_id, len(written_fields), len(created_entities), len(job_errors),
    )


async def run_knowledge_discovery_job(status: JobStatus, entity_id: str) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_discovery, status, entity_id)


async def enqueue_knowledge_discovery(entity_id: str) -> JobStatus:
    async def _factory(status: JobStatus) -> None:
        await run_knowledge_discovery_job(status, entity_id)

    return await job_queue.enqueue(
        kind=JobKind.KNOWLEDGE_DISCOVERY,
        label=f"Web-Recherche: {entity_id}",
        coro_factory=_factory,
    )
```

(`DiscoveredEntity`/`DiscoveryOutput`/`_parse_discovery_output` aus Aufgabe 2 gehören in
dieselbe Datei, oberhalb von `_build_user_prompt`.)

`jobs/queue.py` — `JobKind`-Enum um `KNOWLEDGE_DISCOVERY = "knowledge_discovery"` ergänzen
(nach `INTERVIEW`, vor `RECOMMENDATION`, Zeile ~51).

## AK dieser Phase
- [ ] `enqueue_knowledge_discovery("actors/tom-hanks")` (oder eine andere echte, öffentliche
      Test-Entity) läuft durch: Job-Status `done`, `result.written_fields` enthält `"body"`
      **oder** `result.errors` erklärt nachvollziehbar warum nicht.
- [ ] Der geschriebene `body` steht danach unter `service.find_entity(entity_id).body` (echte
      Persistenz geprüft, nicht nur der Job-Result).
- [ ] Mindestens ein Testlauf erzeugt eine neue verknüpfte Entity mit `owner == "web"` und
      einer validen Relationship auf die Ausgangs-Entity.
- [ ] Ein bewusst kaputter Modell-Output (z.B. Prompt-Text ohne die Marker, manuell simuliert)
      lässt `_parse_discovery_output` ein leeres `DiscoveryOutput` liefern, keinen Crash.
- [ ] Parser-Trefferquote über 5-10 echte Läufe protokolliert (Konfidenz-Ausweis README).

## Doc-Updates
- [ ] `docs/code-map.md` — „KI-Layer / Gemma"-Zeile um `jobs/knowledge_discovery_job.py`,
      `knowledge/slug.py` ergänzen.

## Report-Back
