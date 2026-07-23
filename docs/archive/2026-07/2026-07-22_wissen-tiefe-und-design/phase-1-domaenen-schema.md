# Phase 1 — Domänen: Feld-Fragen und bevorzugte Quellen

**Rating:** standard (Schema-Erweiterung nach vorhandenem Muster, keine offene Designfrage)

Fundament für Phase 2 und 4. Beides gehört in die Domänen-Dateien, weil dort schon steht, welche
Merkmale ein Typ hat — Frage und Feld wandern damit gemeinsam, und ein neues Merkmal bringt seine
Frage automatisch mit, statt in einer Frageliste vergessen zu werden.

## Kontext — das musst du lesen

- `backend/photofant/knowledge/domains.py` — `FieldDef` (Zeile 21), `EntityType` (32),
  `Domain` (41), `fields_for` (71), Parser ab Zeile 96 (`_parse_private`, `_parse_fields`).
- `backend/photofant/knowledge/domains/private.yaml` und `movies.yaml` — die zwei
  mitgelieferten Domänen. Die Kommentare darin sind Nutzer-Doku; neue Schlüssel werden dort
  genauso erklärt.
- `backend/photofant/api/knowledge.py` — `EntityFieldDefDto`, `EntityTypeDto`, `DomainDto`
  (die Domänen-Route liefert sie ans Frontend).
- `frontend/src/app/models/knowledge.model.ts` — `EntityFieldDefDto`, `EntityType`, `DomainDto`.
- `docs/conventions/python.md`

## Zwei neue Schlüssel

### 1. `question` pro Merkmal (für das Interview)

```yaml
  - name: Person
    folder: people
    fields:
      - key: beruf
        label: Beruf
        question: Was macht {name} beruflich?
```

- Optional. Fehlt er, wird das Merkmal im Interview **nicht** gefragt (bleibt aber ein Merkmal,
  das Web-Recherche oder Handeintrag füllen können).
- `{name}` ist der einzige Platzhalter und wird durch den Namen der befragten Person ersetzt.
  Kommt er nicht vor, bleibt die Frage unverändert.

### 2. `preferred_sources` (für die Web-Recherche)

Auf Domänen-Ebene als Vorgabe, optional pro Typ feiner:

```yaml
name: Movies
preferred_sources:
  - wikipedia.org

entity_types:
  - name: Actor
    folder: actors
    preferred_sources:
      - imdb.com
      - wikipedia.org
```

- Beide optional, Liste von Hosts (ohne Schema, ohne `www.`).
- **Auflösung:** Hat der Typ eine eigene Liste, gilt **nur** sie. Sonst die der Domäne. Sonst leer.
- Private Domänen ignorieren den Schlüssel komplett (sie gehen nie ins Netz) — beim Laden nicht
  verbieten, aber in Phase 4 nie anwenden.

## AK dieser Phase

1. `FieldDef` trägt `question: str | None = None`; `Domain` und `EntityType` tragen je
   `preferred_sources: tuple[str, ...] = ()`.
2. `Domain.questions_for(type_name)` liefert die Merkmale des Typs, die eine Frage haben, in
   YAML-Reihenfolge.
3. `Domain.preferred_sources_for(type_name)` löst nach der Regel oben auf (Typ schlägt Domäne).
4. Eine Domänen-Datei **ohne** die neuen Schlüssel lädt unverändert (Rückwärtskompatibilität).
5. Ungültige Werte (kein String, keine Liste) werfen `DomainLoadError` mit Klartext-Meldung —
   wie die bestehenden Parser-Fehler.
6. Die Domänen-Route liefert beide Angaben ans Frontend; `DomainDto`/`EntityFieldDefDto` im
   Frontend-Model sind entsprechend erweitert.
7. `uv run ruff check .`, `npm run lint`, `npm run build` grün.

## Checkliste

### Backend — Schema

- [x] `FieldDef.question: str | None = None`.
- [x] `EntityType.preferred_sources: tuple[str, ...] = ()`,
      `Domain.preferred_sources: tuple[str, ...] = ()`.
- [x] `_parse_fields`: `question` einlesen (String oder fehlend; anderes → `DomainLoadError`).
- [x] Neuer Parser `_parse_preferred_sources(raw, path)`: fehlend → `()`; Liste von nicht-leeren
      Strings → Tupel, dabei `www.`-Präfix und Groß-/Kleinschreibung normalisieren; sonst
      `DomainLoadError`.
- [x] In `load_domain` und im Typ-Parser aufrufen.
- [x] `Domain.questions_for(type_name) -> tuple[FieldDef, ...]` — filtert `fields_for` auf
      Einträge mit gesetzter `question`.
- [x] `Domain.preferred_sources_for(type_name) -> tuple[str, ...]` — Typ-Liste falls nicht leer,
      sonst Domänen-Liste.

### Backend — YAML-Inhalte

- [x] `private.yaml`, Typ `Person`: Fragen ergänzt für `geburtstag`, `beruf`, `wohnort`,
      `vorlieben`, `beziehung`.
- [x] `private.yaml`, Typ `Pet`: Fragen für `art`, `geburtstag`, `eigenheiten`.
- [x] `private.yaml`: **keine** `preferred_sources` (private Domäne).
- [x] `movies.yaml`: `preferred_sources: [wikipedia.org]` auf Domänen-Ebene;
      Typ `Actor` zusätzlich `[imdb.com, wikipedia.org]`; Typ `Movie` `[imdb.com, wikipedia.org]`.
- [x] `movies.yaml`: Fragen bei den Actor-/Movie-Feldern weggelassen.
- [x] Beide YAMLs: die neuen Schlüssel im Kopf-Kommentar in einem Satz erklärt.

### Backend — API

- [x] `EntityFieldDefDto.question: str | None`.
- [x] `EntityTypeDto.preferred_sources: list[str]`, `DomainDto.preferred_sources: list[str]`.
- [x] Bau-Stelle der DTOs entsprechend befüllt.

### Frontend — Model

- [x] `EntityFieldDefDto.question: string | null`.
- [x] `EntityType.preferred_sources: string[]`, `DomainDto.preferred_sources: string[]`.

### Tests

- [x] Domäne ohne neue Schlüssel lädt (AK 4).
- [x] `questions_for` liefert nur Felder mit Frage, in YAML-Reihenfolge.
- [x] `preferred_sources_for`: Typ schlägt Domäne; ohne Typ-Liste greift die Domäne; ohne beides leer.
- [x] `www.`-Normalisierung.
- [x] Ungültiger Wert → `DomainLoadError` (question + preferred_sources je ein Test).

### Docs

- [x] `docs/models.md`: die zwei neuen Domänen-Schlüssel dokumentiert.

## Report-Back

Neue Testdatei `backend/tests/test_knowledge_domains.py` (7 Tests, alle grün) statt Ergänzung
einer bestehenden — es gab noch keine dedizierte Parser-Testdatei für `domains.py`.
`uv run ruff check .` (geänderte Dateien) und `npm run lint`/`npm run build` grün. Ein
mypy-Fehler in `api/knowledge.py` (Zeile ~376, `dict()` gegen `Sequence[Row[Any]]`) ist
Vorbelastung — per `git stash` bestätigt, dass er unverändert vor dieser Phase schon da war
(vorher Zeile 364, reine Zeilenverschiebung durch die neuen DTO-Felder).
