# P2 · Phase 3 — Galerie-Grid

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (`GET /api/assets`)
- [docs/design/README.md](../../design/README.md) — Galerie-View, Foto-Grid, Sub-Toolbar; `docs/design/js/gallery.jsx` als Verhaltens-Referenz
- [docs/conventions/angular.md](../../conventions/angular.md), [ngrx.md](../../conventions/ngrx.md)

## Akzeptanzkriterien

- Justiertes Brick-Layout exakt nach Prototyp (flex-wrap, `flex-grow: ar`, Spacer am Gruppen-Ende), Gruppierung nach Monat mit Header.
- Server-seitige Pagination: beim Scrollen ans Seitenende lädt die nächste Seite nach (kein Virtual Scroll); Skeleton-Zellen während des Ladens.
- Dichte-Umschalter (sm/md/lg) und Sortierung (Datum/Größe, asc/desc) wirken sofort.
- `gallery`- und `filters`-NgRx-Slices nach ngrx.md (EntityAdapter für Assets, Filter/Sort/Group/Density im filters-Slice).

## Checkliste

- [ ] `store/gallery/` (EntityAdapter, Pagination-State, Load-Effects) + `store/filters/` (sort, group, density; Facetten-Felder vorbereitet für P6)
- [ ] `AssetService` (eine Methode pro Endpoint, typisierte Dtos in `@photofant/models`)
- [ ] Galerie-Feature: Grid-Komponente (Brick-Layout, Monats-Header), Zellen-Komponente (Hover-Veil, AR aus Dto, Lazy-Img mit Platzhalter)
- [ ] Sub-Toolbar: Ergebnis-Count, Sort-Button, Dichte-Control (Gruppier-Segment + Chips folgen in P6)
- [ ] Nachlade-Trigger (IntersectionObserver am Listenende via Host-Element)
- [ ] Doc-Update: docs/routes.md anlegen (Route ↔ Endpoint-Mapping)

## Report-Back
