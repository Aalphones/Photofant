# Phase 2 — Interaktionsmodell: Dropdown / Freitext-Fuzzy / exakte Auswahl

**Komplexität:** heikel (neue Architektur-Entscheidung: Fuzzy-Suche-Ansatz) · **Status:** pending

**Voraussetzung:** Phase 1 abgeschlossen (stabiler Such-Modus, sonst baut diese Phase auf wackeligem Fundament).

## Kontext (vor dem Bauen lesen)

- `frontend/src/app/ui/search-box/search-box.ts` — komplette Komponente (Autocomplete-Logik, `suggestions` computed Zeile 78-101, Debounce-Pipelines Zeile 54-66 + 106-112).
- `frontend/src/app/models/asset.model.ts:1-2` — `SEARCH_MODES` Konstante.
- `backend/photofant/api/assets.py:52-55` (Enum), `:488-518` (Such-Zweige in `list_assets`).
- `backend/photofant/db/models.py` — Asset-Modell für verfügbare Textfelder (`caption`, verknüpfte Tags, verknüpfte Person über Face/Instance — exakten Join-Pfad hier prüfen, nicht raten).
- `frontend/src/app/store/filters/filters.actions.ts` — `setPersonId`, `setTagIds` (bereits vorhandene exakte Filter, hier nur wiederverwendet, keine neue Action).
- Gewünschtes Verhalten (User-Vorgabe wörtlich):
  1. Klick in Suchleiste (leer) → Dropdown mit Suchverlauf (**bereits vorhanden**, `recentSearches` in `search-box.ts:26-32, 188-223` — nur prüfen, ob es nach den Changes noch korrekt greift).
  2. Beginn der Eingabe → Freitextsuche über Personen-Namen, Caption und Tags, **fuzzy**, Galerie filtert direkt (debounced), Dropdown aktualisiert Vorschläge.
  3. Maus/Pfeiltasten-Auswahl → erst hier kommt die exakte/semantische Filterung:
     - Person gewählt → exakter Personen-Filter (`filtersActions.setPersonId`, **bereits so**).
     - Tag gewählt → exakter Tag-Filter (aktuell **nicht** so: `search-box.ts:179-184` schickt den Tag-Text als freien `q`-String statt `filtersActions.setTagIds`, kann bei mehrdeutigen Tag-Namen falsche Treffer liefern).
     - Semantik gewählt → CLIP-Suche (**bereits so**, Reset-Bug ist in Phase 1 gefixt).

## Architektur-Entscheidung: Fuzzy-Freitextsuche (→ ADR-015)

Nächste freie ADR-Nummer: **015** (015 ist frei — höchste bislang reservierte Nummer ist 014 aus `docs/planning/2026-07-01_p27-gemma-integration/README.md`, geprüft per Grep über `docs/planning/` und `docs/decisions/`).

**Optionen:**
- **A — rapidfuzz über In-Memory-Kandidaten (empfohlen):** Backend holt Kandidaten (Tag-Namen, Personen-Namen, Captions der aktuell gefilterten Asset-Menge) aus der DB, scored mit `rapidfuzz` (neue Dependency, `uv add rapidfuzz`), sortiert nach Score. Einfach, keine Migration, keine neue SQLite-Extension. **Risiko (🟡):** Skaliert nur gut, solange die Kandidatenmenge klein bleibt (Tag-/Personen-Namen sind das immer; Captions bei sehr großen Bibliotheken evtl. nicht — kurzer Row-Count-Check zu Beginn der Phase, bei > ~50k Assets Kandidaten auf die bereits gefilterte Teilmenge statt der Gesamtbibliothek beschränken, nicht die ganze Tabelle scoren).
- **B — SQLite FTS5 mit Trigram-Tokenizer:** Echtes DB-seitiges Fuzzy/Prefix-Matching, skaliert besser, aber neue virtuelle Tabelle + Migration + Sync-Pflicht (Caption/Tag/Personen-Name-Änderungen müssten den FTS-Index nachziehen) — mehr Fläche für Drift-Bugs, siehe `vector_index.py`-Vorbild (dort ist das bereits gelöst, aber für einen zweiten Index nochmal Aufwand).

**Entscheidung:** A, mit dem 🟡-Fallback auf gefilterte statt globale Kandidatenmenge. Bei Kompatibilitätsproblemen/Skalierungsgrenzen in der Praxis ist B der dokumentierte Ausweg (nicht in diesem Plan umgesetzt).

## Akzeptanzkriterien

- Neuer `q_mode = 'text'`: liefert Treffer, deren Tag-Name **oder** Caption **oder** verknüpfter Personen-Name fuzzy zur Eingabe passt (auch bei einem Tippfehler), sortiert nach Score.
- `search-box.ts` dispatcht beim Tippen (Freitext-Debounce, bestehende 300 ms-Pipeline) `searchActions.setQuery` mit `mode` implizit `'text'` statt bisher `'tags'` — Reducer-Default und `setQuery`-Case entsprechend angepasst (baut auf dem Phase-1-Fix auf, dort wurde `setQuery` bereits angefasst).
- Tag-Auswahl aus dem Dropdown ruft `filtersActions.setTagIds([tag.id])` statt textueller `q`-Suche.
- Dropdown-Suggestions (Personen/Tags/Semantik-Eintrag) funktionieren unverändert wie bisher; Suchverlauf beim Fokussieren einer leeren Suchleiste bleibt unverändert.
- Row-Count-Check dokumentiert (Ist-Größe der Bibliothek, kurze Notiz im Report-Back) — Entscheidungsgrundlage für die 🟡-Fallback-Schwelle.

## Umsetzung

- [ ] `rapidfuzz` als Backend-Dependency hinzufügen (`mode-dependencies`-Konventionen beachten).
- [ ] `SEARCH_MODES` (Frontend) und `SearchMode`-Enum (Backend, `assets.py:52-55`) um `'text'` erweitern.
- [ ] `assets.py` `list_assets`: neuer Zweig `q_mode == SearchMode.TEXT` — Kandidaten (Tag-Name, Caption, Personen-Name über bestehenden Join-Pfad) holen, mit `rapidfuzz.process` scoren, Ergebnis-IDs analog zum bestehenden `semantic_score_map`-Muster (Zeile 511-518) in die Query einspeisen.
- [ ] `search-box.ts`: Freitext-Dispatch auf `mode: 'text'` umstellen (Reducer/Action ggf. um `mode`-Parameter in `setQuery` erweitern, falls nicht schon durch Phase 1 vorbereitet).
- [ ] `search-box.ts` `selectSuggestion()`, Zweig `type === 'tag'`: `filtersActions.setTagIds({ tagIds: [item.id!] })` dispatchen statt `searchActions.setQuery`.
- [ ] Recent-Search-Eintrag für Tag-Auswahl (`saveRecentSearch`) ggf. anpassen, falls er bisher an der `q`-Textsuche hing.
- [ ] Doc: `docs/routes.md` (`q_mode=text` ergänzen), `docs/models.md` falls neue Felder/Indizes, `docs/code-map.md` (Zeile „Suche") falls neue Dateien entstehen (Namensschema beachten: bleibt in `api/search.py`? Nein — Logik lebt in `assets.py`, code-map bleibt korrekt, nur prüfen ob Zeile 20 noch stimmt).
- [ ] `docs/decisions/015-fuzzy-freitextsuche.md` anlegen (10-Zeilen-ADR: Kontext/Optionen/Entscheidung/Konsequenzen, Inhalt siehe Abschnitt oben).

## Report-Back
