# Phase 2 — Frontend Galerie-Grid: Stapel-Icon + Tab-Konsolidierung

**Tier:** standard
**Status:** pending

Setzt Phase 1 voraus (`stack_size`/`stack_group_id`/`kind`/`version_id` auf `AssetDto`).

---

## Kontext (was vorher lesen)

- `frontend/src/app/models/asset.model.ts` — `MEDIA_TYPES`, `AssetDto`
- `frontend/src/app/features/galerie/sub-toolbar/` — `sub-toolbar.html`/`.ts` (Segment-Umschalter)
- `frontend/src/app/features/galerie/grid/`, `features/galerie/cell/` — Grid-Zelle
- `frontend/src/app/store/filters/` — `MediaType`-State
- `frontend/src/app/store/gallery/` — Query-Parameter, Pagination

---

## Abnahme-Kriterien

- [ ] `MEDIA_TYPES` hat nur noch `['photos', 'faces']`; `edits` als eigener Typ entfernt
- [ ] Sub-Toolbar-Segment zeigt nur „Alles / Fotos / Gesichter" (kein Edits-Button mehr)
- [ ] Grid-Zelle zeigt ein Stapel-Icon (klein, unten rechts) wenn `stack_size > 1`
- [ ] Jede Zelle zeigt ihr **eigenes** Thumbnail (Original- oder Version-Bild) — kein
  Bild wird durch das eines anderen Gruppenmitglieds ersetzt
- [ ] Sortierung im Grid folgt dem **eigenen** Datum jedes Eintrags (kein Gruppen-Aggregat)
- [ ] Bulk-Auswahl (Auswählen-Modus): jeder Eintrag (Original, jede Version, jedes
  `original_id`-Kind) ist ein eigenständiges Auswahl-Ziel — keine implizite Kopplung

---

## Checkliste

### Models & Store

- [ ] `MEDIA_TYPES` in `asset.model.ts` auf `['photos', 'faces']` kürzen; `AssetDto` um
  `stack_size: number`, `stack_group_id: number | null`, `kind: 'asset' | 'version'`,
  `version_id: number | null` ergänzen (Typen siehe P21-README Kontrakt)
- [ ] Store/Filters: `MediaType`-Reducer/Selectors anpassen, falls `'edits'` irgendwo als
  Literal referenziert wird (`grep -rn "'edits'"` vor dem Löschen, nicht blind ersetzen)

### Sub-Toolbar

- [ ] `sub-toolbar.html`/`.ts`: Segment-Liste ergibt sich automatisch aus `MEDIA_TYPE_LIST`
  (falls hart codiert, korrigieren)
- [ ] Leerer-Zustand-Text für `mediaType() === 'edits'` in `galerie.html` entfernen
  (`frontend/src/app/features/galerie/galerie.html:41-43` + `:56`)

### Grid-Zelle — Stapel-Icon

- [ ] `cell`-Komponente: `@if (asset.stack_size > 1) { <div class="cell__stack-badge">...</div> }`
- [ ] Icon nach vorhandenem Icon-Set (`pf-icon`) wählen — kein neues Custom-SVG ohne Rücksprache
- [ ] SCSS: Badge unten rechts, dezent (Idiotensicherheits-Gate: muss ohne Erklärung als
  „hier gibt's mehr" lesbar sein — kurzer Tooltip „Stapel · N Versionen" reicht)
- [ ] Thumbnail-URL-Auflösung berücksichtigt `kind`: `'version'` → Version-Thumbnail-Route,
  `'asset'` → bestehende `/assets/{id}/thumbnail`

### Bulk-Aktionen

- [ ] Prüfen: `ui/bulk-bar/` und Auswahl-Logik in `galerie.ts` — läuft eine Bulk-Aktion über
  `asset.id`? Version-Pseudo-Einträge haben eine `asset.id` (des Originals) **und** eine
  `version_id` — sicherstellen, dass Löschen/Favorisieren auf dem richtigen physischen
  Objekt landet (Version löschen ≠ Original löschen)

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
