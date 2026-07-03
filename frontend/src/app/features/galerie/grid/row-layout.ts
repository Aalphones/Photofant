import type { AssetDto, FaceGalleryItemDto } from '@photofant/models';

export const GRID_GAP = 8; // .grid__row { gap: 8px }
export const GRID_PADDING = 16; // :host { padding: 0 16px } — einseitig, total 32px

export const ROW_HEIGHT = (baseHeight: number): number => baseHeight + GRID_GAP;

export interface LayoutItem {
  kind: 'asset' | 'face';
  id: number;
  ratio: number;
  assetId?: number;
}

export interface VirtualRow {
  items: LayoutItem[];
}

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

export function computeRows(
  items: LayoutItem[],
  containerWidth: number,
  baseHeight: number,
  gap: number = GRID_GAP
): VirtualRow[] {
  if (items.length === 0) return [];
  const innerWidth = containerWidth - 2 * GRID_PADDING;
  if (innerWidth <= 0) return items.map((item: LayoutItem) => ({ items: [item] }));

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
