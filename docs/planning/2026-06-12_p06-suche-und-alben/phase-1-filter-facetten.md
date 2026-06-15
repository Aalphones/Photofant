# P6 · Phase 1 — Filter-Facetten

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Filter-Params, Facets)
- [docs/design/README.md](../../design/README.md) — Filter-Rail, Sub-Toolbar; `docs/design/js/gallery.jsx`
- [Konzept](../../Konzept-Photofant.md) §10, §16 (Faceting über tag/asset_tag)

## Akzeptanzkriterien

- Backend: Filter-Params + Facetten-Counts (indizierte Queries; Counts beziehen sich auf die aktuelle Filtermenge).
- Rail nach Prototyp: Accordion-Facetten, Checkbox-Rows, Qualitäts-Slider (Custom-Drag), Tag-Suchfeld; Personen-Facette als Platzhalter (P7).
- `filters`-Slice vollständig; aktive Filter als Chips (entfernbar) in der Sub-Toolbar; Filter in der URL (Query-Params) für Reload/Bookmark.
- Gruppier-Segment (Monat/Quelle; Person folgt P7).

## Checkliste

- [ ] Backend-Filter + Facets-Aggregation
- [ ] Rail-Komponenten (Facette, Checkbox-Row, Slider) nach Prototyp-Maßen
- [ ] Chips + URL-Sync (Router-Query ↔ filters-Slice)
- [ ] Gruppierung nach Quelle im Grid
- [ ] Doc-Update: routes.md

## Report-Back
