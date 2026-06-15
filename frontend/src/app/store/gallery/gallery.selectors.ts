import { createSelector } from '@ngrx/store';
import type { AssetDto, AssetGroup, GroupKey } from '@photofant/models';
import { filtersFeature } from '../filters/filters.reducer';
import { galleryFeature } from './gallery.reducer';

const {
  selectAll,
  selectTotal,
  selectPage,
  selectPageSize,
  selectIsLoading,
  selectError,
} = galleryFeature;

function formatMonthLabel(dateStr: string | null): string {
  if (!dateStr) return 'Unbekannt';
  const date = new Date(dateStr);
  return new Intl.DateTimeFormat('de-DE', { month: 'long', year: 'numeric' }).format(date);
}

function buildGroups(assets: AssetDto[], group: GroupKey): AssetGroup[] {
  const map = new Map<string, AssetDto[]>();

  for (const asset of assets) {
    let key: string;
    if (group === 'source') {
      key = asset.source ?? 'Unbekannt';
    } else if (group === 'person') {
      key = 'Unbekannt';
    } else {
      key = formatMonthLabel(asset.created_at ?? asset.imported_at);
    }
    const bucket = map.get(key);
    if (bucket !== undefined) {
      bucket.push(asset);
    } else {
      map.set(key, [asset]);
    }
  }

  return [...map.entries()].map(([label, groupAssets]) => ({ label, assets: groupAssets }));
}

const selectHasMore = createSelector(
  selectTotal, selectPage, selectPageSize,
  (total: number, page: number, pageSize: number) => total > page * pageSize
);

const selectGroups = createSelector(
  selectAll, filtersFeature.selectGroup,
  (assets: AssetDto[], group: GroupKey) => buildGroups(assets, group)
);

const selectFetchParams = createSelector(
  selectPage, selectPageSize,
  filtersFeature.selectSort, filtersFeature.selectOrder, filtersFeature.selectFavourite,
  (page, pageSize, sort, order, favourite) => ({ page, pageSize, sort, order, favourite })
);

export const gallerySelectors = {
  selectAll,
  selectTotal,
  selectPage,
  selectPageSize,
  selectIsLoading,
  selectError,
  selectHasMore,
  selectGroups,
  selectFetchParams,
};
