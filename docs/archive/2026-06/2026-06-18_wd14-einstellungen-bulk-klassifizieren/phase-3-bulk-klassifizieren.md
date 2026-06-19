# Phase 3 — Gallery Bulk-Klassifizieren

> Rating: **standard** · Status: complete

## Kontext (vorher lesen)

- `frontend/src/app/ui/bulk-bar/bulk-bar.ts` + `bulk-bar.html` — aktuelle Aktionen: Taggen (add/remove), Zu Album; kein Klassifizieren-Trigger
- `frontend/src/app/features/galerie/galerie.ts` + `galerie.html` — BulkBar ist eingebunden; `onBulkTag()` und `onAddToAlbum()` als Handler; kein ClassifyService injiziert
- `frontend/src/app/ui/rerun-dialog/rerun-dialog.ts` — `RerunDialog`-Component; Inputs: `scopeLabel`, `presets`; Outputs: `confirm` (RerunPayload), `cancel`
- `frontend/src/app/services/classify.service.ts` — `rerun({ asset_ids, steps, caption_preset_id? })` → HTTP POST `/api/classify/rerun`
- `frontend/src/app/features/galerie/lightbox/lightbox.ts` — Referenz-Implementation: `openRerunDialog()` / `onRerunConfirm()` / `onRerunCancel()`

**Was bereits funktioniert:** Lightbox-Button „Klassifizieren" öffnet `RerunDialog` für das aktive Bild. Diese Phase baut denselben Flow für die Mehrfachauswahl.

## Architektur-Entscheidung: Dialog-Owner

`RerunDialog` braucht `presets` (Caption-Preset-Liste für die Dropdown). Diese kommen aus dem Store (`presetsSelectors.selectPresets`). Optionen:

| Option | Pro | Contra |
|---|---|---|
| A) Dialog in Galerie-Komponente | Galerie besitzt Kontext (selectedIds), keine Prop-Durchreichung | Galerie wird größer |
| B) Dialog in BulkBar | BulkBar ist self-contained | BulkBar braucht neues `presets`-Input + Store-Kopplung |

**Wahl: A** — analog zu Lightbox (die ihren Dialog auch selbst besitzt). BulkBar emittiert nur ein Signal `rerunAction`, Galerie zeigt den Dialog.

## Checkliste

### bulk-bar.ts

- [x] Output hinzufügen: `readonly rerunAction = output<void>()`
- [x] Methode: `protected openRerunDialog(): void { this.rerunAction.emit(); }`

### bulk-bar.html

- [x] Neuen Divider + Button nach dem Album-Block einfügen:
  ```html
  <div class="bulkbar__divider"></div>
  <button class="bulkbar__action" (click)="openRerunDialog()">
    <pf-icon name="refresh" [size]="15" />
    Klassifizieren
  </button>
  ```

### galerie.ts

- [x] `ClassifyService` aus `@photofant/services` importieren und injizieren: `private readonly classifyService = inject(ClassifyService)`
- [x] `presetsSelectors` aus `@photofant/store` importieren
- [x] `presetsActions` aus `@photofant/store` (war noch nicht importiert, ergänzt)
- [x] `RerunDialog` + `RerunPayload` aus `@photofant/ui` importieren; `RerunDialog` in `imports`-Array
- [x] Signal: `protected readonly showBulkRerunDialog = signal(false)`
- [x] Presets aus Store: `protected readonly bulkRerunPresets = this.store.selectSignal(presetsSelectors.selectPresets)`
- [x] Handler `onBulkRerunOpen()` implementiert
- [x] Handler `onBulkRerunConfirm(payload: RerunPayload)` implementiert
- [x] Handler `onBulkRerunCancel()` implementiert

### galerie.html

- [x] `(rerunAction)="onBulkRerunOpen()"` an `<pf-bulk-bar>` verdrahtet
- [x] RerunDialog nach dem BulkBar-Block eingefügt

### ui/index.ts

- [x] `RerunPayload` war bereits exportiert — kein Änderungsbedarf

## Akzeptanzkriterien

- Bulk-Bar zeigt „Klassifizieren"-Button sobald ≥1 Bild selektiert.
- Klick öffnet RerunDialog mit Scope-Label „N Bilder".
- Bestätigen startet Rerun-Job für alle selektierten IDs; Auswahl wird danach aufgehoben.
- Abbrechen schließt Dialog, Auswahl bleibt.

## Report-Back
