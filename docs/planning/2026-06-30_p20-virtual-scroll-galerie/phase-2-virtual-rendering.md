# Phase 2 — @tanstack/angular-virtual Integration

**Komplexität:** heikel (neues Package, ResizeObserver, Pagination-Trigger-Umbau)

## Kontext — relevante Files lesen

- `phase-1-layout-engine.md` — fertige Utilities (`computeRows`, `buildLayoutItems`, Konstanten)
- [`frontend/src/app/features/galerie/grid/grid.ts`](../../../frontend/src/app/features/galerie/grid/grid.ts) — wird umgebaut
- [`frontend/src/app/features/galerie/grid/grid.html`](../../../frontend/src/app/features/galerie/grid/grid.html) — wird umgebaut
- [`frontend/src/app/features/galerie/grid/grid.scss`](../../../frontend/src/app/features/galerie/grid/grid.scss) — neue Styles für Virtual-Row
- [`frontend/src/app/features/galerie/galerie.ts`](../../../frontend/src/app/features/galerie/galerie.ts) — `allAssets`-Signal existiert schon (aktuell `private`)
- [`frontend/src/app/features/galerie/galerie.html`](../../../frontend/src/app/features/galerie/galerie.html) — Input an `pf-galerie-grid` ändert sich
- `README.md` — finale AK + Smoke-Checkliste

## Abnahmekriterien

- `@tanstack/angular-virtual` ist installiert und im `package.json` eingetragen.
- `GalerieGrid` akzeptiert `assets: input.required<AssetDto[]>()` statt `groups`.
- Alle Rows haben uniforme Höhe `baseHeight + GRID_GAP` — kein `measureElement`.
- `virtualizer.getTotalSize()` bestimmt die Höhe des Scroll-Spacers → korrekter Scrollbalken.
- Wenn `virtualizer.range.endIndex >= rows().length - OVERSCAN - 3` und `hasMore()` und nicht `isLoading()` → `loadMore.emit()` (wie heute der Sentinel).
- Scrollen zurück nach oben triggert kein Fetching.
- Selektion (`toggleSelected`, `rangeSelect`, `selectAll`) ist store-basiert und funktioniert unverändert.

## Checkliste

### Dependency installieren

- [ ] `npm install @tanstack/angular-virtual` im `frontend/`-Ordner
- [ ] Prüfen: `@tanstack/angular-virtual` re-exportiert `injectVirtualizer` — ggf. direkt aus `@tanstack/virtual` importieren falls Angular-Adapter nur ein Wrapper ist

### `galerie.ts` anpassen

- [ ] `allAssets` von `private` auf `protected` hochstufen (wird als Grid-Input übergeben)
- [ ] `groups`-Signal und `GalerieGrid`-Import anpassen (Input-Typ ändert sich)

### `galerie.html` anpassen

- [ ] `[groups]="groups()"` → `[assets]="allAssets()"` in `<pf-galerie-grid>`

### `grid.ts` umbauen

- [ ] Import `ElementRef`, `viewChild` ergänzen (für Scroll-Container-Ref)
- [ ] Input umbenennen: `groups: input.required<AssetGroup[]>()` → `assets: input.required<AssetDto[]>()`
- [ ] Neues Input: `hasMore = input<boolean>(false)` (für Pagination-Guard)
- [ ] `containerWidth = signal<number>(0)`; ResizeObserver auf Host-Element in `afterNextRender`:
  ```typescript
  const ro = new ResizeObserver(([entry]) => {
    if (entry) containerWidth.set(entry.contentRect.width);
  });
  ro.observe(hostEl.nativeElement);
  this.destroyRef.onDestroy(() => ro.disconnect());
  ```
- [ ] `rows = computed((): VirtualRow[] => computeRows(buildLayoutItems(assets(), facesMap()), containerWidth(), baseHeight(), GRID_GAP))`
- [ ] Scroll-Container als `viewChild`:
  ```typescript
  private readonly scrollEl = viewChild.required<ElementRef<HTMLElement>>('scrollContainer');
  ```
- [ ] Virtualizer anlegen:
  ```typescript
  protected readonly virtualizer = injectVirtualizer(() => ({
    count: this.rows().length,
    getScrollElement: () => this.scrollEl().nativeElement,
    estimateSize: () => ROW_HEIGHT(this.baseHeight()),
    overscan: OVERSCAN,
  }));
  ```
  mit `const OVERSCAN = 5` als Konstante oben in der Datei.
- [ ] Pagination-Trigger als `effect`:
  ```typescript
  effect(() => {
    const range = this.virtualizer.range();
    const totalRows = this.rows().length;
    if (
      range !== null &&
      range.endIndex >= totalRows - OVERSCAN - 3 &&
      this.hasMore() &&
      !this.isLoading()
    ) {
      this.loadMore.emit();
    }
  });
  ```
- [ ] `IntersectionObserver` auf `#loadSentinel` **entfernen** — wird durch obigen `effect` ersetzt
- [ ] `groupIds`-Methode entfernen (war für `selectAll` pro Group — wird nicht mehr benötigt)
- [ ] `facesForAsset`-Methode bleibt (wird im Template pro Asset-Item in der Row gebraucht)
- [ ] Hilfsmethode `isAssetSelected` bleibt

### `grid.html` umbauen

Scroll-Container muss ein echtes Element mit `overflow-y: auto` und fixer Höhe sein, damit tanstack eine `getScrollElement`-Referenz hat:

```html
<div class="grid__scroll-container" #scrollContainer>
  <!-- Tanstack-Spacer: gibt dem Scrollbereich die korrekte Gesamthöhe -->
  <div [style.height.px]="virtualizer.getTotalSize()" style="position: relative; width: 100%;">

    @for (vRow of virtualizer.getVirtualItems(); track vRow.key) {
      <div
        class="grid__virtual-row"
        [style.position]="'absolute'"
        [style.top.px]="0"
        [style.transform]="'translateY(' + vRow.start + 'px)'"
        [style.height.px]="vRow.size"
        [style.width]="'100%'"
      >
        @if (rows()[vRow.index]; as row) {
          @for (item of row.items; track item.id) {
            @if (item.kind === 'asset') {
              <pf-galerie-cell
                [asset]="assetById(item.id)"
                [baseHeight]="baseHeight()"
                [density]="density()"
                [selectionMode]="selectionMode()"
                [isSelected]="isAssetSelected(item.id)"
                [isArmed]="isArmed()"
                (openAsset)="onOpenAsset($event)"
                (batchBind)="onBatchBind($event)"
                (rangeSelect)="onRangeSelect($event)"
              />
            } @else {
              <div
                class="grid__face-wrapper"
                [style.width.px]="baseHeight()"
                [style.height.px]="baseHeight()"
              >
                <pf-face-cell
                  [face]="faceById(item.id)"
                  [cellSize]="baseHeight()"
                  (openFace)="onOpenFace($event)"
                />
              </div>
            }
          }
          <div class="grid__spacer"></div>
        }
      </div>
    }

  </div>

  @if (isLoading()) {
    <div class="grid__skeleton-row">
      @for (cell of skeletonCells; track cell.index) {
        <div
          class="grid__skeleton-cell"
          [style.height.px]="baseHeight()"
          [style.flex-grow]="cell.ratio"
          [style.flex-basis.px]="cell.ratio * baseHeight()"
        ></div>
      }
      <div class="grid__spacer"></div>
    </div>
  }
</div>
```

**Wichtig:** Für `assetById` und `faceById` braucht das Grid eine Map-Lookup-Methode, da `rows()` nur IDs enthält:
- [ ] `assetMap = computed((): Map<number, AssetDto> => new Map(assets().map((asset) => [asset.id, asset])))`
- [ ] `protected assetById(id: number): AssetDto { return this.assetMap().get(id)! }`
- [ ] Für Faces: `facesMap()` bereits vorhanden, aber Face-Objekte selbst nicht direkt. Entweder:
  - Option A: `LayoutItem` um `face?: FaceGalleryItemDto` erweitern (direkte Referenz statt ID-Lookup) — sauberer
  - Option B: `faceMap = computed((): Map<number, FaceGalleryItemDto> => ...)` aus `facesMap()`-Werten

  **Empfehlung Option A:** In `buildLayoutItems` das face-Objekt direkt in `LayoutItem` stecken. Spart Lookup-Map im Grid. `LayoutItem` erhält optionales Feld `data?: AssetDto | FaceGalleryItemDto`.

  Konkret `LayoutItem` erweitern:
  ```typescript
  export interface LayoutItem {
    kind: 'asset' | 'face';
    id: number;
    ratio: number;
    assetId?: number;
    assetData?: AssetDto;      // gefüllt wenn kind === 'asset'
    faceData?: FaceGalleryItemDto; // gefüllt wenn kind === 'face'
  }
  ```
  Dann im Template direkt `item.assetData` / `item.faceData` nutzen — kein Map-Lookup nötig.

- [ ] `buildLayoutItems` in `row-layout.ts` entsprechend erweitern (Phase-1-Datei anpassen)

### `grid.scss` anpassen

- [ ] `.grid__scroll-container` hinzufügen:
  ```scss
  .grid__scroll-container {
    height: 100%;
    overflow-y: auto;
    padding: 0 16px 24px;
    // padding aus :host hierher verschieben — :host bekommt kein padding mehr
  }
  ```
- [ ] `:host { padding: ... }` entfernen (geht ins `.grid__scroll-container`)
- [ ] `.grid__virtual-row` hinzufügen:
  ```scss
  .grid__virtual-row {
    display: flex;
    flex-wrap: nowrap; // wir kontrollieren den Inhalt pro Row
    gap: 8px;
    align-items: flex-start;
    padding-bottom: 8px; // ersetzt Row-Gap nach unten
  }
  ```
- [ ] `.grid__sentinel` entfernen (nicht mehr benötigt)

### `galerie.html` — `hasMore` übergeben

- [ ] `[hasMore]="hasMore()"` zu `<pf-galerie-grid>` ergänzen

### Scroll-Container festlegen

**Ist-Stand:** `galerie.scss` hat kein `overflow-y: auto` — der Scroll läuft am Window/Document.
@tanstack/virtual braucht einen echten DOM-Scroll-Container. Zwei Optionen:

**Option A — Window-Scroll-Modus (kein Layout-Umbau):**
`injectVirtualizer` mit `getScrollElement: () => document.documentElement`.
Prüfen ob `@tanstack/angular-virtual` das unterstützt (v3 sollte es via `documentElement`).
Kein CSS-Umbau nötig.

**Option B — Expliziter Scroll-Container (sauberer, robuster):**
`.galerie__main` wird zum Scroll-Container:
```scss
// galerie.scss
:host           { display: flex; flex-direction: column; height: 100vh; }
.galerie__body  { flex: 1; min-height: 0; overflow: hidden; }
.galerie__main  { height: 100%; overflow-y: auto; }
```
`getScrollElement: () => this.scrollEl().nativeElement` (ein `viewChild` auf `.galerie__main`
oder auf dem Grid-Host — dann vom Grid nach oben referenzieren).

**Entscheidung für den Plan: Option A zuerst probieren** (0 CSS-Aufwand). Schlägt der Window-Scroll-Modus in @tanstack/angular-virtual fehl, auf Option B wechseln. In FINDINGS.md eintragen.

### Docs

- [ ] `docs/code-map.md` aktualisieren: `row-layout.ts` eintragen, `#loadSentinel` als entfernt markieren

## 🟡 Risiken

- **Scroll-Element:** `injectVirtualizer` braucht ein Element mit `overflow-y: auto/scroll`, keinen Window-Scroll. Falls `.galerie__main` bisher kein Overflow-Container ist, muss das Layout angepasst werden — kleines CSS-Risiko, aber gut isoliert.
- **`virtualizer.range()` API:** Die Angular-Adapter-API kann sich von der React-Doku unterscheiden. `range` ist möglicherweise kein Signal sondern ein Getter — Implementierung prüfen, ggf. `effect(() => { const r = virtualizer.range; ... })` anpassen.
- **`rows()[vRow.index]` kann `undefined` sein** wenn tanstack kurzzeitig einen alten Index rendert während `rows()` sich neu berechnet. Das `@if (rows()[vRow.index]; as row)` fängt das ab.
- **`assetMap` recomputed bei jeder Page:** O(n) über alle geladenen Assets. Bei 6000 Assets ca. 6000-Entry-Map — akzeptabel, computed wird gecacht.

## Report-Back
