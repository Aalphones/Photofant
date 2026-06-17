# P6 · Phase 2 — 3-Modi-Suche

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (`q`/`q_mode`)
- [docs/design/README.md](../../design/README.md) — Suche (3 Modi), Top-Bar; `docs/design/js/app.jsx`
- Semantic-Endpoint aus P5 Phase 4

## Akzeptanzkriterien

- Search-Box in der Top-Bar mit Mode-Pills (Desktop) / Cycle-Button (Mobile); Modi: Tags (Tag-Match), Caption (Volltext, SQLite FTS oder LIKE — bei Umsetzung messen), Semantisch (CLIP, lila Akzent nach Prototyp).
- Autocomplete bei Fokus: Tag-Vorschläge (Tags-Modus), letzte Suchen (übrige Modi).
- Semantik-Ergebnisse in Score-Reihenfolge; Mischbetrieb mit Rail-Filtern definiert (Filter schneiden die Treffermenge).
- `search`-Slice nach Konzept §15.

## Checkliste

- [x] Caption-Volltext im Backend (FTS5-Spike: lohnt es gegenüber LIKE bei erwarteter Bestandsgröße? → FINDINGS)
- [x] `q`/`q_mode`-Integration in `GET /api/assets` + Semantik-Pfad über den Vektor-Index
- [x] Search-Box-Komponente (Pills, Autocomplete-Dropdown, Debounce)
- [x] `store/search/` + Verdrahtung mit gallery-Load
- [x] Doc-Update: routes.md

## Report-Back

**FTS5-Entscheidung:** LIKE gewählt, kein FTS5 — Begründung in FINDINGS.md.

**Backend:**
- `GET /api/assets` + `q` + `q_mode` (tags/caption/semantic); Semantic-Pfad: CLIP-Text-Embedding → Vektor-Index Top-200 → SQL-Filter → Python-Sort nach Score → paginiert.
- Neuer `GET /api/tags?query=&page=&page_size=` Endpoint für Autocomplete + spätere Tag-Verwaltung.

**Frontend:**
- `store/search/` Slice: Actions `setQuery`/`setMode`/`clear`, Reducer `{ q, mode }`, keine eigenen Effects.
- `gallery.effects.ts`: `onFiltersChange$` reagiert jetzt auch auf alle Search-Actions → Gallery-Reset.
- `gallery.selectors.ts`: `selectFetchParams` enthält `q`/`qMode` aus dem Search-Slice.
- `ui/search-box/` Komponente: Mode-Pills (Desktop), Cycle-Button (Mobile), 300ms-Debounce-Dispatch, Autocomplete-Dropdown (Tags-Modus → `/api/tags`, andere Modi → localStorage Recent Searches).
- TopBar: statisches Input durch `<pf-search-box />` ersetzt.
