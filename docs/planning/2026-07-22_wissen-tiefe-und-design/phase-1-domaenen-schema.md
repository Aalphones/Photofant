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

- [ ] `FieldDef.question: str | None = None`.
- [ ] `EntityType.preferred_sources: tuple[str, ...] = ()`,
      `Domain.preferred_sources: tuple[str, ...] = ()`.
- [ ] `_parse_fields`: `question` einlesen (String oder fehlend; anderes → `DomainLoadError`).
- [ ] Neuer Parser `_parse_preferred_sources(raw, path)`: fehlend → `()`; Liste von nicht-leeren
      Strings → Tupel, dabei `www.`-Präfix und Groß-/Kleinschreibung normalisieren; sonst
      `DomainLoadError`.
- [ ] In `load_domain` und im Typ-Parser aufrufen.
- [ ] `Domain.questions_for(type_name) -> tuple[FieldDef, ...]` — filtert `fields_for` auf
      Einträge mit gesetzter `question`.
- [ ] `Domain.preferred_sources_for(type_name) -> tuple[str, ...]` — Typ-Liste falls nicht leer,
      sonst Domänen-Liste.

### Backend — YAML-Inhalte

- [ ] `private.yaml`, Typ `Person`: Fragen ergänzen für `geburtstag`, `beruf`, `wohnort`,
      `vorlieben`, `beziehung`. Ton wie im Interview — persönlich, nicht formularhaft, z.B.
      `Wo wohnt {name}?` / `Was macht {name} beruflich?` / `Wann hat {name} Geburtstag?` /
      `Was mag {name} besonders — Hobbys, Vorlieben, Eigenheiten?` /
      `In welcher Beziehung steht {name} — Partnerschaft, Familie?`
- [ ] `private.yaml`, Typ `Pet`: Fragen für `art`, `geburtstag`, `eigenheiten`.
- [ ] `private.yaml`: **keine** `preferred_sources` (private Domäne).
- [ ] `movies.yaml`: `preferred_sources: [wikipedia.org]` auf Domänen-Ebene;
      Typ `Actor` zusätzlich `[imdb.com, wikipedia.org]`; Typ `Movie` `[imdb.com, wikipedia.org]`.
- [ ] `movies.yaml`: Fragen bei den Actor-/Movie-Feldern **weglassen** — öffentliche Domänen
      laufen über die Web-Recherche, nicht über das Interview.
- [ ] Beide YAMLs: die neuen Schlüssel im Kopf-Kommentar in einem Satz erklären (die Dateien
      sind Nutzer-Doku und frei editierbar).

### Backend — API

- [ ] `EntityFieldDefDto.question: str | None`.
- [ ] `EntityTypeDto.preferred_sources: list[str]`, `DomainDto.preferred_sources: list[str]`.
- [ ] Bau-Stelle der DTOs entsprechend befüllen.

### Frontend — Model

- [ ] `EntityFieldDefDto.question: string | null`.
- [ ] `EntityType.preferred_sources: string[]`, `DomainDto.preferred_sources: string[]`.

### Tests

- [ ] Domäne ohne neue Schlüssel lädt (AK 4).
- [ ] `questions_for` liefert nur Felder mit Frage, in YAML-Reihenfolge.
- [ ] `preferred_sources_for`: Typ schlägt Domäne; ohne Typ-Liste greift die Domäne; ohne beides leer.
- [ ] `www.`-Normalisierung.
- [ ] Ungültiger Wert → `DomainLoadError`.

### Docs

- [ ] `docs/models.md`: die zwei neuen Domänen-Schlüssel dokumentieren.

## Report-Back
