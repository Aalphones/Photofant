import { createSelector } from '@ngrx/store';
import type { AssetDto, AssetGroup, GroupKey } from '@photofant/models';
import { filtersFeature } from '../filters/filters.reducer';
import { personsFeature } from '../persons/persons.reducer';
import { searchFeature } from '../search/search.reducer';
import { galleryFeature } from './gallery.reducer';

const {
  selectAll,
  selectEntities,
  selectTotal,
  selectPage,
  selectPageSize,
  selectIsLoading,
  selectError,
  selectLightboxId,
  selectFacets,
  selectSelectionMode,
  selectSelectedIds,
  selectFaceItems,
  selectFaceTotal,
} = galleryFeature;

function formatMonthLabel(dateStr: string | null): string {
  if (!dateStr) return 'Unbekannt';
  const date = new Date(dateStr);
  return new Intl.DateTimeFormat('de-DE', { month: 'long', year: 'numeric' }).format(date);
}

function buildGroups(
  assets: AssetDto[],
  group: GroupKey,
  personNames: Map<number, string>,
): AssetGroup[] {
  const map = new Map<string, AssetDto[]>();

  for (const asset of assets) {
    let key: string;
    if (group === 'source') {
      key = asset.source ?? 'Unbekannt';
    } else if (group === 'person') {
      const personId = (asset as AssetDto & { person_id?: number }).person_id;
      key = personId != null ? (personNames.get(personId) ?? 'Unbekannt') : 'Unbekannt';
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

// Adapter's `selectTotal` is shadowed onto the loaded-entity count, so read the
// server-side total straight from feature state for "are there more pages" logic.
const selectServerTotal = createSelector(
  galleryFeature.selectGalleryState,
  (state) => state.total,
);

const selectHasMore = createSelector(
  selectServerTotal, selectPage, selectPageSize,
  (total: number, page: number, pageSize: number) => total > page * pageSize
);

const selectPersonNameMap = createSelector(
  personsFeature.selectAll,
  (persons) => {
    const map = new Map<number, string>();
    for (const person of persons) {
      map.set(person.id, person.name ?? 'Unbekannt');
    }
    return map;
  },
);

const selectGroups = createSelector(
  selectAll, filtersFeature.selectGroup, selectPersonNameMap,
  (assets: AssetDto[], group: GroupKey, personNames: Map<number, string>) =>
    buildGroups(assets, group, personNames)
);

const selectFetchParams = createSelector(
  selectPage, selectPageSize,
  filtersFeature.selectSort, filtersFeature.selectOrder, filtersFeature.selectFavourite,
  filtersFeature.selectSources, filtersFeature.selectQualityMin, filtersFeature.selectTagIds,
  filtersFeature.selectCollectionId, filtersFeature.selectPersonId, filtersFeature.selectFramings,
  filtersFeature.selectMediaType,
  searchFeature.selectQ, searchFeature.selectMode,
  (page, pageSize, sort, order, favourite, sources, qualityMin, tagIds, collectionId, personId, framings, mediaType, q, qMode) =>
    ({ page, pageSize, sort, order, favourite, sources, qualityMin, tagIds, collectionId, personId, framings, mediaType, q, qMode })
);

const selectFaceHasMore = createSelector(
  selectFaceTotal, selectPage, selectPageSize,
  (total: number, page: number, pageSize: number) => total > page * pageSize,
);

const selectLightboxAsset = createSelector(
  selectEntities,
  selectLightboxId,
  (entities, lightboxId) => (lightboxId != null ? (entities[lightboxId] ?? null) : null),
);

const selectLightboxCurrentIndex = createSelector(
  selectAll,
  selectLightboxId,
  (assets: AssetDto[], lightboxId: number | null) =>
    lightboxId != null ? assets.findIndex((asset: AssetDto) => asset.id === lightboxId) : -1,
);

const selectLightboxHasPrev = createSelector(
  selectLightboxCurrentIndex,
  (index: number) => index > 0,
);

const selectLightboxHasNext = createSelector(
  selectAll,
  selectLightboxCurrentIndex,
  selectHasMore,
  (assets: AssetDto[], index: number, hasMore: boolean) =>
    index >= 0 && (index < assets.length - 1 || hasMore),
);

const selectLightboxNavContext = createSelector(
  selectAll,
  selectLightboxId,
  selectHasMore,
  selectIsLoading,
  (assets: AssetDto[], lightboxId: number | null, hasMore: boolean, isLoading: boolean) =>
    ({ assets, lightboxId, hasMore, isLoading }),
);

const selectHashMap = createSelector(
  selectEntities,
  (entities): Record<number, string> => {
    const map: Record<number, string> = {};
    for (const asset of Object.values(entities)) {
      if (asset) { map[asset.id] = asset.content_hash; }
    }
    return map;
  }
);

export const gallerySelectors = {
  selectAll,
  selectTotal,
  selectServerTotal,
  selectPage,
  selectPageSize,
  selectIsLoading,
  selectError,
  selectHasMore,
  selectGroups,
  selectFetchParams,
  selectFacets,
  selectLightboxId,
  selectLightboxAsset,
  selectLightboxHasPrev,
  selectLightboxHasNext,
  selectLightboxNavContext,
  selectSelectionMode,
  selectSelectedIds,
  selectPersonNameMap,
  selectFaceItems,
  selectFaceTotal,
  selectFaceHasMore,
  selectHashMap,
};
