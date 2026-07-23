# Phase 6 — Face-Grid/-Cell: Checkbox-Overlay + Klick-Verdrahtung

**Komplexität:** standard (Muster ist durch den bestehenden Asset-Cell 1:1 vorgegeben).

**Voraussetzung:** Phase 5 abgeschlossen (Face-Selection-State existiert).

## Kontext (lesen vor dem Start)

- [frontend/src/app/features/galerie/face-cell/face-cell.ts](../../../frontend/src/app/features/galerie/face-cell/face-cell.ts) —
  komplette Datei (46 Zeilen), heutiger Zustand: `host: { '(click)': 'onCellClick()' }` öffnet
  **immer** die Lightbox, kein Auswahl-Zweig.
- [frontend/src/app/features/galerie/face-cell/face-cell.html](../../../frontend/src/app/features/galerie/face-cell/face-cell.html) —
  komplette Datei (32 Zeilen).
- [frontend/src/app/features/galerie/face-cell/face-cell.scss](../../../frontend/src/app/features/galerie/face-cell/face-cell.scss) —
  komplette Datei (100 Zeilen) — `.face-cell__badge--upscaled` (Zeile 70-82) zeigt **bereits**
  ein Sparkle-Icon bei `face().is_upscaled` — sobald Phase 4 dieses Feld setzt, taucht das Badge
  ohne weiteres Zutun auf.
- [frontend/src/app/features/galerie/face-grid/face-grid.ts](../../../frontend/src/app/features/galerie/face-grid/face-grid.ts) —
  komplette Datei (65 Zeilen).
- [frontend/src/app/features/galerie/face-grid/face-grid.html](../../../frontend/src/app/features/galerie/face-grid/face-grid.html) —
  komplette Datei (28 Zeilen).
- [frontend/src/app/features/galerie/cell/cell.ts:96-133](../../../frontend/src/app/features/galerie/cell/cell.ts#L96) —
  `GalerieCell.onCellClick`/`onPickClick` — **exaktes Vorbild** für die Klick-Präzedenz
  (Armed-Modus schlägt Selection-Modus, Shift-Klick löst Range statt Toggle aus). Anders als
  `GalerieCell` injiziert `FaceCell` **keinen** `Store` — bleibt eine reine Input/Output-
  Komponente (bestehende Konvention dieser Komponentenfamilie, siehe `onOpenFace`/`onBindFace` in
  `galerie.ts`, die schon heute alles dispatcht, was von `FaceGrid` hochgereicht wird). Diese
  Phase folgt der **bestehenden Face-Komponenten-Konvention**, nicht 1:1 der `GalerieCell`-eigenen
  (Store-Injection) — nur das Klick-Präzedenz-Verhalten wird übernommen.
- [frontend/src/app/features/galerie/cell/cell.html:13-25](../../../frontend/src/app/features/galerie/cell/cell.html#L13) —
  `.cell__pick`-Button-Markup — Vorlage für den neuen `.face-cell__pick`.
- [frontend/src/app/features/galerie/cell/cell.scss:1-78](../../../frontend/src/app/features/galerie/cell/cell.scss#L1) —
  `.cell__pick`-CSS + Host-Zustände (`cell--selected`, `cell--selmode`) — Vorlage.
- [frontend/src/app/features/galerie/galerie.html:58-80](../../../frontend/src/app/features/galerie/galerie.html#L58) —
  `pf-face-grid`/`pf-galerie-grid`-Einbindung — der Foto-Zweig (Zeile 66-79) bekommt heute
  `[selectionMode]`, `[selectedIds]`, `[isArmed]`, `(rangeSelect)` — der Face-Zweig (Zeile 58-64)
  **keines** davon. Genau diese Lücke schließt diese Phase.
- [frontend/src/app/features/galerie/galerie.ts:100](../../../frontend/src/app/features/galerie/galerie.ts#L100) —
  `isArmed` (bereits vorhandenes `computed`), wird an `pf-face-grid` neu durchgereicht.
- README Risiken — Stack-Pseudo-Einträge teilen ihre `id` mit dem Eltern-Face; Auswahl trifft
  bewusst dieselbe ID wie das Eltern-Face.

## Aufgabe 1 — `FaceCell`: Inputs, Outputs, Klick-Präzedenz

`frontend/src/app/features/galerie/face-cell/face-cell.ts` — komplett ersetzen durch:

```typescript
import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import type { FaceGalleryItemDto } from '@photofant/models';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-face-cell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './face-cell.html',
  styleUrl: './face-cell.scss',
  host: {
    '(click)': 'onCellClick($event)',
    '[class.face-cell--selected]': 'isSelected()',
    '[class.face-cell--selmode]': 'selectionMode()',
  },
})
export class FaceCell {
  readonly face          = input.required<FaceGalleryItemDto>();
  readonly cellSize      = input<number>(160);
  readonly isSelected    = input<boolean>(false);
  readonly selectionMode = input<boolean>(false);
  readonly isArmed       = input<boolean>(false);

  readonly openFace    = output<{ faceId: number; assetId: number | null; versionId: number | null }>();
  readonly toggleSelect = output<number>();
  readonly rangeSelect  = output<number>();

  protected readonly label = computed((): string => {
    const face = this.face();
    if (face.person_name) { return face.person_name; }
    if (face.age != null) { return `~${face.age} J.`; }
    return 'Gesicht';
  });

  protected readonly scorePercent = computed((): string => {
    const score = this.face().score;
    return score != null ? `${Math.round(score * 100)}%` : '';
  });

  protected readonly isStacked = computed((): boolean =>
    this.face().stack_size > 1
  );

  protected readonly stackTooltip = computed((): string =>
    `Stapel · ${this.face().stack_size} Versionen`
  );

  private emitOpenFace(): void {
    const face = this.face();
    this.openFace.emit({ faceId: face.id, assetId: face.asset_id, versionId: face.version_id });
  }

  protected onCellClick(event: MouseEvent): void {
    if (!this.isArmed() && (this.selectionMode() || event.ctrlKey || event.metaKey || event.shiftKey)) {
      event.stopPropagation();
      if (event.shiftKey) {
        this.rangeSelect.emit(this.face().id);
      } else {
        this.toggleSelect.emit(this.face().id);
      }
      return;
    }
    this.emitOpenFace();
  }

  protected onPickClick(event: MouseEvent): void {
    event.stopPropagation();
    this.toggleSelect.emit(this.face().id);
  }
}
```

**Warum `isArmed()` zuerst geprüft wird:** ist ein Workflow-Slot scharf (Run-Leiste), muss ein
Klick immer `openFace` auslösen, damit der Elternteil (`galerie.ts`, Ternary
`isArmed() ? onBindFace($event) : onOpenFace($event)`) das Gesicht in den Slot bindet — auch wenn
`selectionMode` zufällig gleichzeitig aktiv ist. Exakt dieselbe Präzedenz wie bei `GalerieCell`
(`cell.ts:101-110`).

## Aufgabe 2 — `FaceCell`-Template: Checkbox-Overlay

`frontend/src/app/features/galerie/face-cell/face-cell.html` — vor dem bestehenden
`face-cell__info`-Block (Zeile 13) einfügen:

```html
@if (!isArmed()) {
  <button
    class="face-cell__pick"
    [class.face-cell__pick--selected]="isSelected()"
    (click)="onPickClick($event)"
    [attr.aria-label]="isSelected() ? 'Abwählen' : 'Auswählen'"
    [attr.aria-pressed]="isSelected()"
  >
    @if (isSelected()) {
      <pf-icon name="check" [size]="13" />
    }
  </button>
}
```

## Aufgabe 3 — `FaceCell`-Styles: `.face-cell__pick`

`frontend/src/app/features/galerie/face-cell/face-cell.scss` — Host-Block (Zeile 1-16) erweitern:

```scss
:host {
  display: block;
  position: relative;
  cursor: pointer;
  border-radius: 6px;
  overflow: hidden;
  background: var(--surface-2, #1e1e1e);

  &:hover .face-cell__veil { opacity: 1; }
  &:hover .face-cell__info { opacity: 1; }
  &:hover .face-cell__pick { opacity: 1; }

  &.face-cell--selected {
    outline: 2px solid var(--accent);
    outline-offset: -2px;

    .face-cell__pick { opacity: 1; background: var(--accent); color: #fff; }
  }

  &.face-cell--selmode .face-cell__pick { opacity: 0.6; }
}
```

Neue Regel irgendwo unterhalb (z. B. nach `.face-cell__veil`, Zeile 39):

```scss
.face-cell__pick {
  position: absolute;
  top: 6px;
  left: 6px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,.8);
  background: rgba(0,0,0,.35);
  display: grid;
  place-items: center;
  color: #fff;
  opacity: 0;
  transition: opacity .15s, background .15s;
  backdrop-filter: blur(4px);
}
```

`.face-cell__badge--upscaled` bleibt `top: 4px; right: 4px;` (Zeile 70-82, unverändert) — kein
Kollisionsrisiko mit dem neuen Pick-Button (oben links).

## Aufgabe 4 — `FaceGrid`: Inputs/Outputs durchreichen

`frontend/src/app/features/galerie/face-grid/face-grid.ts` — `input`/`output`-Deklarationen
erweitern (restliche Datei unverändert):

```typescript
  readonly faceItems      = input.required<FaceGalleryItemDto[]>();
  readonly isLoading      = input.required<boolean>();
  readonly selectionMode  = input<boolean>(false);
  readonly selectedFaceIds = input<number[]>([]);
  readonly isArmed        = input<boolean>(false);

  readonly openFace        = output<{ faceId: number; assetId: number | null; versionId: number | null }>();
  readonly loadMore        = output<void>();
  readonly toggleFaceSelect = output<number>();
  readonly rangeFaceSelect  = output<number>();

  protected readonly selectedFaceIdSet = computed((): Set<number> =>
    new Set(this.selectedFaceIds())
  );
```

`computed` zum bestehenden `@angular/core`-Import ergänzen (Zeile 1-11, `computed` fehlt heute).

**Warum ein `Set` statt `.includes()` im Template:** `selectedFaceIds` kann bei „Alle auswählen"
mehrere hundert Einträge enthalten (`FACE_PAGE_SIZE = 500`, siehe `gallery.selectors.ts`) —
`.includes()` pro Kachel und Change-Detection-Zyklus wäre O(n²) über die sichtbare Liste; das
`computed`-`Set` baut sich nur neu, wenn sich `selectedFaceIds()` selbst ändert, Lookup ist O(1).

## Aufgabe 5 — `FaceGrid`-Template durchreichen

`frontend/src/app/features/galerie/face-grid/face-grid.html` — `pf-face-cell` (Zeile 9-13)
erweitern:

```html
<pf-face-cell
  [face]="face"
  [cellSize]="CELL_SIZE"
  [selectionMode]="selectionMode()"
  [isSelected]="selectedFaceIdSet().has(face.id)"
  [isArmed]="isArmed()"
  (openFace)="onOpenFace($event)"
  (toggleSelect)="toggleFaceSelect.emit($event)"
  (rangeSelect)="rangeFaceSelect.emit($event)"
/>
```

## Aufgabe 6 — `Galerie`: Verdrahtung

`frontend/src/app/features/galerie/galerie.html:58-64`, Face-Zweig ersetzen durch:

```html
} @else if (mediaType() === 'faces') {
  <pf-face-grid
    [faceItems]="faceItems()"
    [isLoading]="isLoading()"
    [selectionMode]="selectionMode()"
    [selectedFaceIds]="selectedFaceIds()"
    [isArmed]="isArmed()"
    (openFace)="isArmed() ? onBindFace($event) : onOpenFace($event)"
    (loadMore)="onFaceLoadMore()"
    (toggleFaceSelect)="onToggleFaceSelect($event)"
    (rangeFaceSelect)="onFaceRangeSelect($event)"
  />
```

`frontend/src/app/features/galerie/galerie.ts` — neue Selector-Signale (bei den bestehenden,
Zeile 42-48 herum) ergänzen:

```typescript
  protected readonly selectedFaceIds = this.store.selectSignal(gallerySelectors.selectSelectedFaceIds);
  private readonly faceAnchorId      = this.store.selectSignal(gallerySelectors.selectFaceAnchorId);
```

Neue Methoden (bei `onRangeSelect`, Zeile 239-256, danach einfügen):

```typescript
  protected onToggleFaceSelect(faceId: number): void {
    this.store.dispatch(galleryActions.toggleFaceSelected({ id: faceId }));
  }

  protected onFaceRangeSelect(targetId: number): void {
    const anchorId = this.faceAnchorId();
    if (anchorId === null) {
      this.store.dispatch(galleryActions.toggleFaceSelected({ id: targetId }));
      return;
    }
    const faces = this.faceItems();
    const anchorIndex = faces.findIndex((face) => face.id === anchorId);
    const targetIndex = faces.findIndex((face) => face.id === targetId);
    if (anchorIndex === -1 || targetIndex === -1) {
      this.store.dispatch(galleryActions.toggleFaceSelected({ id: targetId }));
      return;
    }
    const start = Math.min(anchorIndex, targetIndex);
    const end = Math.max(anchorIndex, targetIndex);
    const rangeIds = faces.slice(start, end + 1).map((face) => face.id);
    this.store.dispatch(galleryActions.selectFaceRange({ ids: rangeIds }));
  }
```

`onSelectAllClick` (Zeile 235-237) — mediaType-Zweig ergänzen:

```typescript
  protected onSelectAllClick(): void {
    if (this.mediaType() === 'faces') {
      this.store.dispatch(galleryActions.selectAllFaces({ ids: this.faceItems().map((face) => face.id) }));
      return;
    }
    this.onSelectAll(this.allAssets().map((asset: AssetDto) => asset.id));
  }
```

`selectedCount` (Zeile 128) — **unverändert lassen** (bleibt Asset-only, steuert weiterhin die
bestehende `pf-bulk-bar` für den Foto-Tab). Der Face-Zähler (`selectedFaceCount`) entsteht in
Phase 7 zusammen mit der neuen Face-Bulk-Leiste.

## AK dieser Phase

- [ ] Im Gesichter-Tab „Auswählen" aktivieren → Klick auf ein Gesicht öffnet **nicht** mehr die
      Lightbox, sondern selektiert (Checkbox-Overlay erscheint/färbt sich).
- [ ] Strg/Cmd-Klick auf ein Gesicht selektiert **auch außerhalb** des expliziten
      Auswahl-Modus (analog zum Foto-Tab).
- [ ] Shift-Klick wählt einen zusammenhängenden Bereich (Anker = zuletzt einzeln
      angeklicktes Gesicht).
- [ ] „Alle auswählen" im Gesichter-Tab selektiert alle geladenen Gesichter, im Foto-Tab
      unverändert alle Fotos (Regressionscheck).
- [ ] Ein scharfer Workflow-Slot (Run-Leiste) bindet weiterhin per Klick, auch wenn
      `selectionMode` zufällig aktiv ist (Armed schlägt Selection).
- [ ] Foto-Tab-Auswahl (`GalerieCell`/`pf-galerie-grid`) verhält sich exakt wie vor dieser Phase
      (kein Code dort geändert).

## Doc-Updates

- [ ] `docs/code-map.md` — Zeile „Personen & Faces": `face-grid`/`face-cell` jetzt mit
      Mehrfachauswahl-Fähigkeit vermerken.

## Report-Back

_(nach Umsetzung ausfüllen: Verhalten bei sehr großen Gesichter-Listen, ob das `Set`-Pattern
spürbar war/nicht war)_
