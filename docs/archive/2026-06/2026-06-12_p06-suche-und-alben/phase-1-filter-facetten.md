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

- [x] Backend-Filter + Facets-Aggregation
- [x] Rail-Komponenten (Facette, Checkbox-Row, Slider) nach Prototyp-Maßen
- [x] Chips + URL-Sync (Router-Query ↔ filters-Slice)
- [x] Gruppierung nach Quelle im Grid
- [x] Doc-Update: routes.md

## Report-Back

Backend: `list_assets` akzeptiert jetzt `source[]`, `quality_min`, `tags[]` (AND per Tag).
Response enthält `facets { sources, tags_top }` aus dem gefilterten Set.
Frontend: filters-Slice um `sources/qualityMin/tagIds` + `clearAllFilters` erweitert;
Gallery-Slice speichert `facets: Facets | null`; neue `FilterRail`-Komponente
(3 Accordion-Facetten: Quelle, Qualität, Tags); Sub-Toolbar zeigt aktive
Filter-Chips + "Alle entfernen"; URL-Sync per Router QueryParams.

Abweichung: Framing-Facette weggelassen (kein Backend-Filter-Param für Framing im P6-Kontrakt).
Personen- und Sammlungs-Facette als Platzhalter ebenfalls weggelassen (P7 bzw. P6 Phase 4).
