# P6 · Phase 2 — 3-Modi-Suche

> Rating: standard · Status: pending

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

- [ ] Caption-Volltext im Backend (FTS5-Spike: lohnt es gegenüber LIKE bei erwarteter Bestandsgröße? → FINDINGS)
- [ ] `q`/`q_mode`-Integration in `GET /api/assets` + Semantik-Pfad über den Vektor-Index
- [ ] Search-Box-Komponente (Pills, Autocomplete-Dropdown, Debounce)
- [ ] `store/search/` + Verdrahtung mit gallery-Load
- [ ] Doc-Update: routes.md

## Report-Back
