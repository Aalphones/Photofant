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

- [x] `npm install @tanstack/angular-virtual` im `frontend/`-Ordner
- [x] Prüfen: `@tanstack/angular-virtual` re-exportiert `injectVirtualizer` — ggf. direkt aus `@tanstack/virtual` importieren falls Angular-Adapter nur ein Wrapper ist

### `galerie.ts` anpassen

- [x] `allAssets` von `private` auf `protected` hochstufen (wird als Grid-Input übergeben)
- [x] `groups`-Signal und `GalerieGrid`-Import anpassen (Input-Typ ändert sich)

### `galerie.html` anpassen

- [x] `[groups]="groups()"` → `[assets]="allAssets()"` in `<pf-galerie-grid>`

### `grid.ts` umbauen

- [x] Import `ElementRef`, `viewChild` ergänzen (für Scroll-Container-Ref)
- [x] Input umbenennen: `groups: input.required<AssetGroup[]>()` → `assets: input.required<AssetDto[]>()`
- [x] Neues Input: `hasMore = input<boolean>(false)` (für Pagination-Guard)
- [x] `containerWidth = signal<number>(0)`; ResizeObserver auf Host-Element in `afterNextRender`:
  ```typescript
  const ro = new ResizeObserver(([entry]) => {
    if (entry) containerWidth.set(entry.contentRect.width);
  });
  ro.observe(hostEl.nativeElement);
  this.destroyRef.onDestroy(() => ro.disconnect());
  ```
- [x] `rows = computed((): VirtualRow[] => computeRows(buildLayoutItems(assets(), facesMap()), containerWidth(), baseHeight(), GRID_GAP))`
- [x] Scroll-Container als `viewChild`:
  ```typescript
  private readonly scrollEl = viewChild.required<ElementRef<HTMLElement>>('scrollContainer');
  ```
- [x] Virtualizer anlegen:
  ```typescript
  protected readonly virtualizer = injectVirtualizer(() => ({
    count: this.rows().length,
    getScrollElement: () => this.scrollEl().nativeElement,
    estimateSize: () => ROW_HEIGHT(this.baseHeight()),
    overscan: OVERSCAN,
  }));
  ```
  mit `const OVERSCAN = 5` als Konstante oben in der Datei.
- [x] Pagination-Trigger als `effect`:
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
- [x] `IntersectionObserver` auf `#loadSentinel` **entfernen** — wird durch obigen `effect` ersetzt
- [x] `groupIds`-Methode entfernen (war für `selectAll` pro Group — wird nicht mehr benötigt)
- [x] **Deviation:** `facesForAsset`-Methode **entfernt statt behalten** — mit Option A
  (Faces direkt in `LayoutItem.faceData`, siehe unten) gibt es keinen Per-Asset-Lookup
  mehr, das Template iteriert bereits flach über `row.items`. `facesForAsset` wäre toter
  Code gewesen.
- [x] Hilfsmethode `isAssetSelected` bleibt
- [x] **Deviation:** `onSelectAll(ids: number[])` → `onSelectAll()` ohne Parameter, liest
  `assets()` selbst (kein `groupIds` mehr, das die IDs geliefert hat). Output-Typ
  (`number[]`) unverändert, nur der interne Aufrufer fällt weg — siehe FINDINGS.md
  (aktuell keine UI-Stelle ruft `onSelectAll` noch auf, war vorher der Gruppen-Button).

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

**Umgesetzt als Option A direkt** (siehe Empfehlung unten) — kein Map-Lookup im Grid nötig,
`assetMap`/`assetById`/`faceById` daher **nicht** angelegt. Template nutzt
`item.assetData`/`item.faceData` direkt (Zugriff über `assetOf(item)`/`faceOf(item)`-Helper
mit dokumentierter Invariante statt rohem `!`-Zugriff im Template).

Ursprüngliche Alternative (nicht umgesetzt, zur Nachvollziehbarkeit belassen):
- [ ] ~~`assetMap = computed((): Map<number, AssetDto> => new Map(assets().map((asset) => [asset.id, asset])))`~~
- [ ] ~~`protected assetById(id: number): AssetDto { return this.assetMap().get(id)! }`~~
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

- [x] `buildLayoutItems` in `row-layout.ts` entsprechend erweitern (Phase-1-Datei anpassen)

### `grid.scss` anpassen

- [x] `.grid__scroll-container` hinzufügen:
  ```scss
  .grid__scroll-container {
    height: 100%;
    overflow-y: auto;
    padding: 0 16px 24px;
    // padding aus :host hierher verschieben — :host bekommt kein padding mehr
  }
  ```
- [x] `:host { padding: ... }` entfernen (geht ins `.grid__scroll-container`)
- [x] `.grid__virtual-row` hinzufügen:
  ```scss
  .grid__virtual-row {
    display: flex;
    flex-wrap: nowrap; // wir kontrollieren den Inhalt pro Row
    gap: 8px;
    align-items: flex-start;
    padding-bottom: 8px; // ersetzt Row-Gap nach unten
  }
  ```
- [x] `.grid__sentinel` entfernen (nicht mehr benötigt)

### `galerie.html` — `hasMore` übergeben

- [x] `[hasMore]="hasMore()"` zu `<pf-galerie-grid>` ergänzen

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

- [x] `docs/code-map.md` aktualisieren: `row-layout.ts` eintragen, `#loadSentinel` als entfernt markieren

## 🟡 Risiken

- **Scroll-Element:** `injectVirtualizer` braucht ein Element mit `overflow-y: auto/scroll`, keinen Window-Scroll. Falls `.galerie__main` bisher kein Overflow-Container ist, muss das Layout angepasst werden — kleines CSS-Risiko, aber gut isoliert.
- **`virtualizer.range()` API:** Die Angular-Adapter-API kann sich von der React-Doku unterscheiden. `range` ist möglicherweise kein Signal sondern ein Getter — Implementierung prüfen, ggf. `effect(() => { const r = virtualizer.range; ... })` anpassen.
- **`rows()[vRow.index]` kann `undefined` sein** wenn tanstack kurzzeitig einen alten Index rendert während `rows()` sich neu berechnet. Das `@if (rows()[vRow.index]; as row)` fängt das ab.
- **`assetMap` recomputed bei jeder Page:** O(n) über alle geladenen Assets. Bei 6000 Assets ca. 6000-Entry-Map — akzeptabel, computed wird gecacht.

## Report-Back

`@tanstack/angular-virtual` installiert, `GalerieGrid` auf flache `assets`-Liste + Virtualizer
umgebaut, `row-layout.ts` um `assetData`/`faceData` erweitert (Option A). Scroll-Container-Frage
zugunsten **Option B** entschieden (expliziter `.grid__scroll-container`, kein Window-Scroll) —
bestätigt durch einen Blick in `shell.scss`: die App scrollt app-weit bereits an
`.shell__content`, nicht am `window`, Window-Virtualisierung hätte also gar nie gefeuert. Das
deckt sich mit der in Phase 3 vorbereiteten ADR-Formulierung, die exakt das gleiche sagt.

**Ripple-Effekte über den Checklisten-Scope hinaus** (Chesterton's Fence — direkt mitgezogen,
da sonst kaputt):
- `features/favoriten/` ist ein zweiter Consumer von `GalerieGrid`, den der Plan nicht auf dem
  Schirm hatte — gleiche Input-/Höhenketten-Anpassung wie `galerie.ts`/`.html`/`.scss`.
- `face-grid.scss` brauchte `:host{height:100%;overflow-y:auto}`, weil es bisher implizit am
  Shell-Level mitscrollte; durch die neue Höhenkette (`galerie.scss` `:host{height:100%}` →
  `.galerie__main{flex:1}`) wäre die Gesichter-Ansicht sonst abgeschnitten worden.

**Deviations vom Plan-Text** (Details in FINDINGS.md):
- `injectVirtualizer` nimmt real `scrollElement: ElementRef` entgegen, nicht
  `getScrollElement: () => …` (Plan-Snippet war React-Doku-Stil).
- `useApplicationRefTick: false` ergänzt — Default `true` kollidierte mit dem eigenen
  Pagination-`effect()` (`NG0101` rekursiver Tick).
- `facesForAsset` entfernt statt behalten (mit Option A toter Code).
- `assetMap`/`assetById` gar nicht angelegt (Option A macht sie überflüssig).

**Offen für Phase 3:** „Alle auswählen" hat aktuell keine UI-Stelle mehr (war der
Gruppen-Header-Button) — Output-Kette funktioniert, nur niemand ruft sie auf. Siehe
FINDINGS.md.

`tsc --noEmit` und `ng build --configuration development` beide sauber durchgelaufen.
