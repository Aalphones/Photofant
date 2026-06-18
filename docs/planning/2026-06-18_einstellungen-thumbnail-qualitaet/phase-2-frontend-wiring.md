# Thumbnails · Phase 2 — Frontend: Cell fragt Größe nach Density an

> Rating: **standard** · Status: pending · Voraussetzung: Phase 1 abgeschlossen

## Kontext (vorher lesen)

- [README.md](README.md) — Density → Thumbnail-Mapping
- `frontend/src/app/features/galerie/cell/cell.ts` — `thumbnailSrc` hardkodiert auf 256
- `frontend/src/app/features/galerie/grid/grid.ts` — kennt `density`, übergibt `baseHeight` an Cell
- `frontend/src/app/models/asset.model.ts` — `BASE_HEIGHTS`, `Density`
- `frontend/src/app/services/asset.service.ts` — `thumbnailUrl(id, size)`

## Mapping

| Density | Thumbnail-Größe |
|---|---|
| `sm` | 256 |
| `md` | 512 |
| `lg` | 1024 |

## Akzeptanzkriterien

- Bei `lg`-Dichte fragt die Cell `?size=1024` an — im Browser-DevTools Network-Tab sichtbar.
- Bei `sm`-Dichte wird `?size=256` angefragt (kein unnötiger Traffic).
- Density-Wechsel in der Toolbar → sofortiger Wechsel der angefragten Thumbnail-Größe.

## Checkliste

- [ ] **`asset.model.ts`**: Konstante `DENSITY_THUMB_SIZE: Record<Density, 256 | 512 | 1024>` ergänzen (`sm→256, md→512, lg→1024`)
- [ ] **`cell.ts`**: `density` als `input.required<Density>()` hinzufügen; `thumbnailSrc` nutzt `DENSITY_THUMB_SIZE[this.density()]` statt hartkodierter `256`; Typsignatur `thumbnailUrl(id, size: 256 | 512 | 1024)` prüfen
- [ ] **`grid.ts`**: `density` bereits als Input vorhanden → an `pf-galerie-cell` als `[density]` weitergeben; Template aktualisieren
- [ ] **`cell.html`**: kein Eingriff erwartet (src-Binding bleibt `thumbnailSrc`)
- [ ] Doc-Update: keine (rein internes Binding, keine API-Änderung)

## Report-Back
