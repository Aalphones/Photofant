# Phase 2 — Frontend Galerie-Grid: Stapel-Icon + Tab-Konsolidierung

**Tier:** standard
**Status:** pending

Setzt Phase 1 voraus (`stack_size`/`list_role`/`effective_date`/`thumbnail_source_id`
auf `AssetDto`).

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
- [ ] Zelle nutzt `thumbnail_source_id` fürs Bild, nicht mehr pauschal die Asset-ID
- [ ] Sortierung im Grid folgt `effective_date`
- [ ] Bulk-Auswahl (Auswählen-Modus) behandelt Stapel-Kopf und Original-Echo als **zwei
  separate, aber verknüpfte** Einträge — keine doppelte Aktion auf demselben physischen Asset
  bei „Alle auswählen"

---

## Checkliste

### Models & Store

- [ ] `MEDIA_TYPES` in `asset.model.ts` auf `['photos', 'faces']` kürzen; `AssetDto` um die vier
  neuen Felder ergänzen (Typen siehe P21-README Kontrakt)
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

### Bulk-Aktionen

- [ ] Prüfen: `ui/bulk-bar/` und Auswahl-Logik in `galerie.ts` — läuft eine Bulk-Aktion über
  `asset.id`? Bei Dual-Listing zeigen zwei Einträge dieselbe zugrundeliegende `asset.id`
  (Original + Stapel-Kopf, wenn Stapel-Kopf ein `version`-Eintrag ist, nicht ein neues Asset) —
  🟡 klären ob das zu Doppel-Aktionen führen kann und wie „Alle auswählen" das entkoppelt

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
