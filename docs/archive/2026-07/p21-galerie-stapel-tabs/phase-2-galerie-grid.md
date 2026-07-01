# Phase 2 — Frontend Galerie-Grid: Stapel-Icon + Tab-Konsolidierung

**Tier:** standard
**Status:** complete

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

- [x] `MEDIA_TYPES` hat nur noch `['photos', 'faces']`; `edits` als eigener Typ entfernt
- [x] Sub-Toolbar-Segment zeigt nur „Fotos / Gesichter" (kein Edits-Button mehr) —
  „Alles" war nie ein eigenes Segment (nur die Treffer-Zahl links), Wortlaut im
  README war ungenau, siehe Report-Back
- [x] Grid-Zelle zeigt ein Stapel-Icon (klein, unten rechts) wenn `stack_size > 1`
- [x] Jede Zelle zeigt ihr **eigenes** Thumbnail (Original- oder Version-Bild) — kein
  Bild wird durch das eines anderen Gruppenmitglieds ersetzt
- [x] Sortierung im Grid folgt dem **eigenen** Datum jedes Eintrags (kein Gruppen-Aggregat)
- [x] Bulk-Auswahl (Auswählen-Modus): `kind==='asset'`-Einträge (Original,
  `original_id`-Kinder) sind eigenständige Auswahl-Ziele. `kind==='version'`-Einträge
  haben **kein** Auswählen/Favorisieren (Backend hat dafür keinen eigenen Endpunkt —
  Ziel-ID wäre sonst fälschlich das Original, siehe Report-Back + FINDINGS → Phase 5)

---

## Checkliste

### Models & Store

- [x] `MEDIA_TYPES` in `asset.model.ts` auf `['photos', 'faces']` kürzen; `AssetDto` um
  `stack_size: number`, `stack_group_id: number | null`, `kind: 'asset' | 'version'`,
  `version_id: number | null` ergänzen (Typen siehe P21-README Kontrakt)
- [x] Store/Filters: `MediaType`-Reducer/Selectors anpassen, falls `'edits'` irgendwo als
  Literal referenziert wird (`grep -rn "'edits'"` vor dem Löschen, nicht blind ersetzen)

### Sub-Toolbar

- [x] `sub-toolbar.html`/`.ts`: Segment-Liste ergibt sich automatisch aus `MEDIA_TYPE_LIST`
  (falls hart codiert, korrigieren)
- [x] Leerer-Zustand-Text für `mediaType() === 'edits'` in `galerie.html` entfernen
  (`frontend/src/app/features/galerie/galerie.html:41-43` + `:56`)

### Grid-Zelle — Stapel-Icon

- [x] `cell`-Komponente: `@if (asset.stack_size > 1) { <div class="cell__stack-badge">...</div> }`
- [x] Icon nach vorhandenem Icon-Set (`pf-icon`) wählen — kein neues Custom-SVG ohne Rücksprache
- [x] SCSS: Badge unten rechts, dezent (Idiotensicherheits-Gate: muss ohne Erklärung als
  „hier gibt's mehr" lesbar sein — kurzer Tooltip „Stapel · N Versionen" reicht)
- [x] Thumbnail-URL-Auflösung berücksichtigt `kind`: `'version'` → Version-Thumbnail-Route,
  `'asset'` → bestehende `/assets/{id}/thumbnail`

### Bulk-Aktionen

- [x] Prüfen: `ui/bulk-bar/` und Auswahl-Logik in `galerie.ts` — läuft eine Bulk-Aktion über
  `asset.id`? Version-Pseudo-Einträge haben eine `asset.id` (des Originals) **und** eine
  `version_id` — sicherstellen, dass Löschen/Favorisieren auf dem richtigen physischen
  Objekt landet (Version löschen ≠ Original löschen)

---

## Report-Back

**Größerer Scope als die Checkliste vermuten lässt:** `MEDIA_TYPES` auf zwei Werte zu
kürzen brach die TS-Typprüfung an jeder Stelle, die noch mit `mediaType() === 'edits'`
verglich — das zog den kompletten Edits-Tab nach sich (nicht nur den Leerer-Zustand-Text):
`galerie.html`/`galerie.ts` (Version-Grid-Branch, Version-Lightbox-Öffnen, Escape-Handling),
sowie den gesamten `edits`-Fetch-Zweig in `gallery.effects.ts`/`gallery.reducer.ts`/
`gallery.actions.ts`/`gallery.selectors.ts`. Die Komponenten `version-cell/` und
`version-lightbox/` wurden komplett gelöscht (waren ausschließlich vom Edits-Tab genutzt,
keine anderen Referenzen mehr). `VersionService` verlor `listVersions` (unbenutzt) und
bekam stattdessen `thumbnailUrl()` für die neue Kachel-Auflösung.

**Kritischer Fund während der Umsetzung (siehe FINDINGS):** Die NgRx-EntityAdapter-Map
im `gallery`-Slice nutzte `asset.id` als Key — das hätte Original und seine
Editor-Versionen gegenseitig überschrieben, weil beide dieselbe `id` tragen. Behoben
durch einen zusammengesetzten Entity-Key (`String(id)` bzw. `` v${version_id} ``).
Ohne diesen Fix hätte die Galerie nie die geforderten N+1 Kacheln pro Stapel gezeigt.

**Bewusst nicht umgesetzt (Backend-Lücke):** Version-Pseudo-Einträge haben kein
Auswählen/Favorisieren bekommen, weil es dafür keinen eigenen Backend-Endpunkt gibt
(Ziel wäre sonst versehentlich das Original). Für ADR-012 vorgemerkt (FINDINGS → Phase 5).

**Bewusst nicht umgesetzt (Feature-Lücke, dokumentiert):** Die Möglichkeit, eine
Editor-Version direkt als ComfyUI-Workflow-Input zu binden, hing bisher am Edits-Tab
(`pf-version-cell` → Bind-Klick) und hat mit dessen Wegfall keinen UI-Einstiegspunkt
mehr. Die Datenverdrahtung (`versionSlotBindings` in `galerie.ts`, Run-Leiste) bleibt
bestehen, wird aber aktuell nie befüllt. Für Phase 4 vorgemerkt (FINDINGS).

**Getestet:** `tsc --noEmit` grün. Kein manuelles Smoke-Testing im Browser (private-
Profil, kein Playwright) — Prüf-Checkliste folgt am Plan-Ende gesammelt für den User.
