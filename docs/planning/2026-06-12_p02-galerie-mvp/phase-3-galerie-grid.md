# P2 · Phase 3 — Galerie-Grid

> Rating: standard · Status: complete

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

- [x] `store/gallery/` (EntityAdapter, Pagination-State, Load-Effects) + `store/filters/` (sort, group, density; Facetten-Felder vorbereitet für P6)
- [x] `AssetService` (eine Methode pro Endpoint, typisierte Dtos in `@photofant/models`)
- [x] Galerie-Feature: Grid-Komponente (Brick-Layout, Monats-Header), Zellen-Komponente (Hover-Veil, AR aus Dto, Lazy-Img mit Platzhalter)
- [x] Sub-Toolbar: Ergebnis-Count, Sort-Button, Dichte-Control (Gruppier-Segment + Chips folgen in P6)
- [x] Nachlade-Trigger (IntersectionObserver am Listenende via `viewChild`-Sentinel in GalerieGrid)
- [x] Doc-Update: docs/routes.md anlegen (Route ↔ Endpoint-Mapping)

## Report-Back

Umgesetzt 2026-06-15. Alle AK erfüllt.

- `store/filters/` — `FiltersState` (sort, order, group, density, favourite); `filtersActions.setSort/setGroup/setDensity/setFavourite`
- `store/gallery/` — EntityAdapter auf `AssetDto`, Pagination (page/pageSize/total/isLoading); `GalleryEffects` hört auf Filter-Änderungen → `reset()`, dann HTTP via `concatLatestFrom(gallerySelectors.selectFetchParams)`
- `AssetService` — `listAssets()`, `getAsset()`, `thumbnailUrl()`, `fileUrl()` (kein `.subscribe()`)
- `GalerieCell` — Flex-Host (`flex-grow: ar`, `flex-basis: ar×base`), lazy `<img>`, Hover-Veil (CSS), Fav-Button (P5 stub), Badges (FLUX/SDXL), Version-Count
- `GalerieGrid` — Brick-Layout per Group, Monats-Header, Skeleton-Cells (CSS-Puls), `IntersectionObserver` auf `#loadSentinel` via `afterNextRender`
- `SubToolbar` — Result-Count, Sort-Cycle-Button (Datum→Größe desc→Größe asc→Datum), Dichte-Segment, Group-Segment; `position: sticky; top: 0`
- `docs/routes.md` angelegt
