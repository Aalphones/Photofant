# Phase 3 — KnowledgeDiscoveryJob: Suche → Gemma → Fakten-Vorschläge

**Komplexität:** heikel (Parsing von Freitext-Output eines kleinen Modells).
**Voraussetzung:** Phase 1 (Capability, Prompt, `search_web()` verifiziert) **und** Phase 2
(Merkmale existieren — der Job listet die Feld-Keys im Prompt auf und mappt Fakten darauf).

> **Geändert am 2026-07-21:** Der Job **schreibt nicht mehr**. Er liest, fragt Gemma und legt
> das Ergebnis als Vorschlagsliste ab. Geschrieben wird erst, wenn der User im Wizard Haken
> setzt — das macht die Übernahme-Route in Phase 4. Dadurch fällt aus diesem Job alles raus,
> was mit `ChangelogService`, `create_entity`, `create_relationship` und
> `invalidate_recommendations` zu tun hatte; der Job braucht **keine Schreib-Session** mehr.

## Kontext (lesen vor dem Start)
- `backend/photofant/jobs/knowledge_update_job.py` — Struktur-Vorbild: Prompt laden,
  Job-Progress-Schritte, `generate()`-Aufruf, `job_queue.set_result`. Dieser Job hier ist
  dasselbe Muster, nur mit einem Suchaufruf davor. **Nicht** `knowledge_patch_job.py` als
  Vorbild nehmen — das ist der Schreibpfad, den wir hier gerade loswerden.
- `backend/photofant/knowledge/service.py` — `find_entity` (Zeile 132). Mehr braucht der Job
  nicht.
- `backend/photofant/knowledge/domains.py` — `Domain.entity_types`, `relationship_types`,
  `fields_for` (neu aus Phase 2).
- `backend/photofant/inference/web_search.py` (Phase 1) — `search_web`, `WebSearchResult`,
  `WebSearchError`.
- `backend/photofant/inference/prompts/knowledge_discovery.md` (Phase 1) — das Ausgabeformat,
  das der Parser unten spiegeln muss. Beide Dateien ändern sich immer zusammen.
- `backend/photofant/knowledge/domains/movies.yaml` — Beispiel-Domäne: die Werte, die Gemma
  als „erlaubte Typen/Beziehungen/Felder" vorgelegt bekommt.

## Aufgabe 1 — Slugify-Helper (Backend, existiert noch nicht)
Wird erst in Phase 4 beim Anlegen vorgeschlagener Entitäten gebraucht, gehört aber
thematisch hierher und ist in zwei Minuten geschrieben. Neue Datei
`backend/photofant/knowledge/slug.py`:

```python
"""Slug-Erzeugung für backend-seitig (nicht vom User im Wizard) erzeugte Entity-IDs.

Spiegelt exakt die Frontend-Logik (entity-wizard-dialog.ts::slugify, Zeile 278-285) —
gleiche Regel, zwei Sprachen, damit IDs unabhängig vom Entstehungsweg gleich aussehen.
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

## Aufgabe 2 — Datenklassen + Parser
Alles in der neuen Datei `jobs/knowledge_discovery_job.py`, oberhalb des Prompt-Baus:

```python
@dataclass
class DiscoveredFact:
    field: str          # Merkmals-Key aus der Domäne, oder "body"
    label: str          # Anzeigename ("Beruf", "Beschreibung")
    value: str
    source: str         # Host der Quelle, z.B. "linkedin.com"
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
```

```python
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
```

```python
def _parse_discovery_output(raw: str, field_labels: dict[str, str]) -> DiscoveryOutput:
    """Defensiver Parser für das 3-Sektionen-Format aus dem Prompt (Phase 1).

    Fehlt eine Sektion oder ist sie leer/„keine" → leeres Ergebnis für genau diese
    Sektion, kein Fehler. Ein komplett unparsbarer Output liefert ein volles
    Leer-Ergebnis — der Wizard zeigt dann „Nichts gefunden", statt zu crashen.

    ``field_labels`` bildet Merkmals-Key → Anzeigename ab (aus ``Domain.fields_for``),
    plus den Sonderfall ``"beschreibung" → "Beschreibung"``.
    """
```
Regeln für die `FAKTEN`-Zeilen:
- `Feld` fehlt oder ist nicht in `field_labels` **und** nicht `"beschreibung"` → Zeile
  verwerfen, `log.warning` mit der Rohzeile. Das Modell erfindet sonst Felder, die keine
  Oberfläche anzeigen und keine Validierung akzeptiert.
- `Feld: beschreibung` → `field="body"`, `label="Beschreibung"`.
- `Wert` fehlt oder leer → verwerfen.
- `Quelle` → `source_url`; `source` ist der Host daraus (`urllib.parse.urlparse(url).netloc`,
  führendes `www.` abschneiden). Keine oder unparsbare URL → `source_url=""`, `source="—"`,
  die Zeile bleibt aber erhalten (die Konfidenz-Pille trägt die Bewertung).
- `Konfidenz` → `float`, geklemmt auf 0..1; fehlt oder unparsbar → `0.5`.

Regeln für `NEUE_ENTITAETEN`: wie gehabt `Titel`/`Typ`/`Beziehung` sind Pflicht, `Info`
optional; unvollständige Zeilen werden mit `log.warning` verworfen. **Keine** Prüfung gegen
die erlaubten Domänen-Typen an dieser Stelle — die macht die Übernahme-Route in Phase 4, weil
dort auch die Fehlermeldung an den User entsteht.

`QUELLEN`: jede nicht-leere Zeile, die mit `http` beginnt.

**Parser-Test (Konfidenz-Ausweis README Punkt 1, vor Phase 4):** nach der ersten echten
Generierung 5-10 Läufe gegen verschiedene reale, bekannte öffentliche Personen fahren und
protokollieren, wie oft Gemma das exakte Format liefert (0 Fakten geparst bei nicht-leerem
Output = Fehlschlag). Unter der Hälfte → **Prompt** nachschärfen (Beispiel-Output aufnehmen),
nicht den Parser komplizierter machen. Das Protokoll gehört als kurze Tabelle ins
`## Report-Back` dieser Phase.

## Aufgabe 3 — Der Job
Neue Datei `backend/photofant/jobs/knowledge_discovery_job.py`:

```python
"""KnowledgeDiscoveryJob (P38) — Websuche + Gemma schlägt Fakten für eine öffentliche Entity
vor. Schreibt NICHTS: das Ergebnis ist eine Vorschlagsliste, die der User im Wizard abhakt
(ADR-031). Der Schreibweg ist die Übernahme-Route in api/knowledge_ai.py.
"""
```

Ablauf in `_run_discovery(status, entity_id)`:
1. Prompt laden (`PromptLibrary().get("knowledge_discovery")`), fehlt er → `RuntimeError`.
2. `SessionLocal()` **nur lesend**: Entity über `find_entity` holen, `None` →
   `EntityNotFoundError`. Domäne über `vault.load_domain(entity.domain)`.
   `domain.private` → `PrivateDomainError` (Verteidigung in der Tiefe, die Route blockt schon).
   Session danach schließen — der Job hält keine Session über den Modell-Call.
3. `search_web(f"{entity.title} {entity.type}", max_results=MAX_SEARCH_RESULTS)` (5),
   `WebSearchError` → `RuntimeError` mit der Meldung der Bibliothek.
4. User-Prompt bauen (Aufgabe 4), `generate(Capability.KNOWLEDGE_DISCOVERY, …,
   system=prompt.text, prompt_version=prompt.version, max_new_tokens=768)`.
   Leere Antwort → `RuntimeError("Das Modell lieferte keine Antwort …")`.
5. `_parse_discovery_output(generation.text, field_labels)`.
6. `job_queue.set_result` mit dem Kontrakt aus der README (`facts`, `entity_suggestions`,
   `sources`, `errors`, `explainability`). `errors` enthält hier nur Parser-Hinweise
   (z.B. „3 Zeilen konnten nicht gelesen werden"), keine Schreibfehler — es wird ja nichts
   geschrieben.

Progress-Schritte: `0.1` Start · `0.3` nach der Suche · `0.5` vor dem Modell-Call · `0.9` nach
dem Parsen. (Die Suche dauert spürbar, der Modell-Call spürbarer — der Fortschrittsbalken soll
nicht bei 10 % einschlafen.)

`explainability.reason` = `"Web-Recherche — Vorschläge, nichts wurde geschrieben."`

Am Ende die `enqueue_knowledge_discovery(entity_id)`-Fabrik wie in
`knowledge_update_job.py`, Label `f"Web-Recherche: {entity_id}"`, Kind
`JobKind.KNOWLEDGE_DISCOVERY`.

`jobs/queue.py` — `JobKind`-Enum um `KNOWLEDGE_DISCOVERY = "knowledge_discovery"` ergänzen
(nach `INTERVIEW`, vor `RECOMMENDATION`, Zeile ~51).

## Aufgabe 4 — User-Prompt
```python
def _build_user_prompt(
    entity: Entity, domain: Domain, results: list[WebSearchResult]
) -> str:
```
Enthält, jeweils eine Zeile bzw. ein Block:
- Titel, Typ, Domäne, Aliase (`"keine"` wenn leer).
- **Erlaubte Merkmals-Keys**: `", ".join(f"{d.key} ({d.label})" for d in domain.fields_for(entity.type))`
  — plus der Hinweis, dass `beschreibung` immer erlaubt ist. Ohne definierte Merkmale:
  `"nur beschreibung"`.
- **Bereits gesetzte Merkmale** mit Wert und Owner — damit das Modell nicht vorschlägt, was
  schon dasteht. Format: `beruf = UX-Designerin (von dir gesetzt)` / `(aus Web-Recherche)`.
- Aktuelle Beschreibung (`entity.body or "(leer)"`), bestehende Beziehungen.
- Erlaubte Entity-Typen und Beziehungstypen der Domäne.
- Die Suchergebnisse als nummerierter Block (`[1] Titel / URL / Snippet`), oder
  `"(keine Suchergebnisse)"`.
- Abschlusssatz: `"Nenne nur Fakten, die durch die Snippets gedeckt sind."`

## AK dieser Phase
- [ ] `enqueue_knowledge_discovery(<echte öffentliche Test-Entity>)` läuft durch: Job-Status
      `done`, `result.facts` enthält mindestens einen Eintrag **oder** `result.errors` erklärt
      nachvollziehbar warum nicht.
- [ ] Nach dem Lauf ist die Entity **unverändert** — Datei-Zeitstempel und Inhalt gleich wie
      vorher. (Der Job schreibt nichts; das ist der Kernunterschied zum ursprünglichen Entwurf.)
- [ ] Jeder gelieferte Fakt hat entweder einen echten Merkmals-Key der Domäne oder `"body"` —
      nie einen erfundenen Feldnamen.
- [ ] Ein bewusst kaputter Modell-Output (Text ohne Marker, manuell simuliert) liefert ein
      leeres `DiscoveryOutput`, keinen Crash.
- [ ] Parser-Trefferquote über 5-10 echte Läufe protokolliert (siehe Aufgabe 2), Tabelle steht
      im Report-Back.

## Doc-Updates
- [ ] `docs/code-map.md` — „KI-Layer / Gemma"-Zeile um `jobs/knowledge_discovery_job.py`,
      `knowledge/slug.py` ergänzen.

## Report-Back
