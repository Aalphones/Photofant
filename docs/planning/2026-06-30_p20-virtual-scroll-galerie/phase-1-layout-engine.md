# Phase 1 — Row-Breaking-Engine

**Komplexität:** heikel (Algorithmus muss mit Browser-Flexbox-Zeilenumbruch übereinstimmen)

## Kontext — relevante Files lesen

- [`frontend/src/app/features/galerie/grid/grid.ts`](../../../frontend/src/app/features/galerie/grid/grid.ts) — aktueller Input-Typ `groups`, `facesMap`, `baseHeight`
- [`frontend/src/app/features/galerie/grid/grid.scss`](../../../frontend/src/app/features/galerie/grid/grid.scss) — `gap: 8px` in `.grid__row`, `padding: 0 16px` in `:host`
- [`frontend/src/app/models/asset.model.ts`](../../../frontend/src/app/models/asset.model.ts) — `AssetDto`, `FaceGalleryItemDto`, `BASE_HEIGHTS`
- `README.md` in diesem Ordner — Kontrakt (`LayoutItem`, `VirtualRow`)

## Abnahmekriterien

- `buildLayoutItems(assets, facesMap)` produziert die richtige Reihenfolge: nach jedem Asset folgen sofort seine Faces (Ratio 1.0) — exakt wie `grid.html` heute rendert.
- `computeRows(items, containerWidth, baseHeight, gap)`:
  - Testfall A: 10 Assets mit Ratio 1.33, `baseHeight=196`, `gap=8`, `containerWidth=1200` (innere Breite 1168) → ca. 2–3 Rows (4–5 Bilder passen pro Zeile).
  - Testfall B: leere `items` → `[]`.
  - Testfall C: `containerWidth <= 0` → jedes Item bekommt eine eigene Row (Fallback).
- Pure Functions, kein DOM-Zugriff, kein Angular.
- Alle Konstanten (`GRID_GAP`, `GRID_PADDING`) als named exports, mit Kommentar zu ihrer CSS-Quelle.

## Checkliste

### Implementierung

- [ ] Neue Datei anlegen: `frontend/src/app/features/galerie/grid/row-layout.ts`

- [ ] Konstanten exportieren:
  ```typescript
  export const GRID_GAP = 8;      // .grid__row { gap: 8px }
  export const GRID_PADDING = 16; // :host { padding: 0 16px } — einseitig, total 32px
  export const ROW_HEIGHT = (baseHeight: number): number => baseHeight + GRID_GAP;
  // Alle Rows haben gleiche Höhe; Gap wird zur Row-Höhe gezählt
  ```

- [ ] Interfaces exportieren (aus README-Kontrakt):
  ```typescript
  export interface LayoutItem {
    kind: 'asset' | 'face';
    id: number;
    ratio: number;
    assetId?: number;
  }

  export interface VirtualRow {
    items: LayoutItem[];
  }
  ```

- [ ] `buildLayoutItems` implementieren:
  ```typescript
  export function buildLayoutItems(
    assets: AssetDto[],
    facesMap: Map<number, FaceGalleryItemDto[]>
  ): LayoutItem[] {
    const result: LayoutItem[] = [];
    for (const asset of assets) {
      result.push({
        kind: 'asset',
        id: asset.id,
        ratio: asset.width && asset.height ? asset.width / asset.height : 4 / 3,
      });
      for (const face of facesMap.get(asset.id) ?? []) {
        result.push({ kind: 'face', id: face.id, ratio: 1, assetId: asset.id });
      }
    }
    return result;
  }
  ```

- [ ] `computeRows` implementieren:
  ```typescript
  export function computeRows(
    items: LayoutItem[],
    containerWidth: number,
    baseHeight: number,
    gap: number = GRID_GAP
  ): VirtualRow[] {
    if (items.length === 0) return [];
    const innerWidth = containerWidth - 2 * GRID_PADDING;
    if (innerWidth <= 0) return items.map((item) => ({ items: [item] }));

    const rows: VirtualRow[] = [];
    let currentItems: LayoutItem[] = [];
    let accumulatedBasis = 0;

    for (const item of items) {
      const itemBasis = item.ratio * baseHeight;
      const itemWithGap = accumulatedBasis === 0 ? itemBasis : itemBasis + gap;

      if (accumulatedBasis + itemWithGap > innerWidth && currentItems.length > 0) {
        rows.push({ items: currentItems });
        currentItems = [item];
        accumulatedBasis = itemBasis;
      } else {
        currentItems.push(item);
        accumulatedBasis += itemWithGap;
      }
    }
    if (currentItems.length > 0) rows.push({ items: currentItems });
    return rows;
  }
  ```

### Docs

- [ ] `docs/code-map.md` prüfen: existiert die Datei? Falls ja, `row-layout.ts` unter Galerie/Grid eintragen.

## 🟡 Risiken

- **Sub-Pixel-Rounding:** Flexbox rundet auf Sub-Pixel; der Algorithmus kann ±1 Row abweichen. Führt zu ±`ROW_HEIGHT`px Drift in der virtuellen Gesamthöhe. Akzeptiert.
- **Faces-Interleaving:** Faces erscheinen im DOM nach dem zugehörigen Asset. `buildLayoutItems` repliziert das. Wenn `facesMap` leer ist (mediaType !== 'all'), werden keine Faces eingebaut — das ist korrekt.

## Report-Back
