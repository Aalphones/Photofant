import { createSelector } from '@ngrx/store';
import type { AssetDto, AssetGroup, FaceGalleryItemDto, GroupKey } from '@photofant/models';
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
  selectLightboxKind,
  selectLightboxFaceId,
  selectLightboxVersionId,
  selectLightboxContextIds,
  selectFacets,
  selectSelectionMode,
  selectSelectedIds,
  selectAnchorId,
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
    } else if (group === 'lineage') {
      // Original als Anker: stack_group_id fasst Original + Editor-Versionen +
      // ComfyUI-original_id-Kinder zusammen (ADR-012); ohne Gruppe ist das Asset sein
      // eigenes Original (Einzelbild ohne Ableitungen).
      key = `Original #${asset.stack_group_id ?? asset.id}`;
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

const FACE_PAGE_SIZE = 500;

const selectFaceHasMore = createSelector(
  selectFaceTotal, selectPage,
  (total: number, page: number) => total > page * FACE_PAGE_SIZE,
);

const selectLightboxAsset = createSelector(
  selectEntities,
  selectLightboxId,
  (entities, lightboxId) => (lightboxId != null ? (entities[lightboxId] ?? null) : null),
);

const selectLightboxHasPrev = createSelector(
  selectAll,
  selectLightboxId,
  selectLightboxContextIds,
  (assets: AssetDto[], lightboxId: number | null, contextIds: number[] | null) => {
    const list = contextIds != null
      ? contextIds.map((id: number) => assets.find((asset: AssetDto) => asset.id === id)).filter((asset): asset is AssetDto => asset != null)
      : assets;
    const index = lightboxId != null ? list.findIndex((asset: AssetDto) => asset.id === lightboxId) : -1;
    return index > 0;
  },
);

const selectLightboxHasNext = createSelector(
  selectAll,
  selectLightboxId,
  selectHasMore,
  selectLightboxContextIds,
  (assets: AssetDto[], lightboxId: number | null, hasMore: boolean, contextIds: number[] | null) => {
    const list = contextIds != null
      ? contextIds.map((id: number) => assets.find((asset: AssetDto) => asset.id === id)).filter((asset): asset is AssetDto => asset != null)
      : assets;
    const index = lightboxId != null ? list.findIndex((asset: AssetDto) => asset.id === lightboxId) : -1;
    return index >= 0 && (index < list.length - 1 || (contextIds == null && hasMore));
  },
);

const selectLightboxNavContext = createSelector(
  selectAll,
  selectLightboxId,
  selectHasMore,
  selectIsLoading,
  selectLightboxContextIds,
  (assets: AssetDto[], lightboxId: number | null, hasMore: boolean, isLoading: boolean, contextIds: number[] | null) =>
    ({ assets, lightboxId, hasMore, isLoading, contextIds }),
);

// P21-Stapel: Face-Modus-Navigation über die Gesichter-Grid-Liste statt der Asset-Liste.
// Version-Pseudo-Einträge teilen ihre `id` mit dem Original-Face (Backend-Design,
// analog zu AssetDto) — Matching braucht darum (id, version_id) statt nur id.
const selectLightboxFaceIndex = createSelector(
  selectFaceItems,
  selectLightboxFaceId,
  selectLightboxVersionId,
  (items: FaceGalleryItemDto[], faceId: number | null, versionId: number | null) =>
    faceId == null ? -1 : items.findIndex((item: FaceGalleryItemDto) => item.id === faceId && item.version_id === versionId),
);

const selectLightboxFaceNavContext = createSelector(
  selectFaceItems,
  selectLightboxFaceIndex,
  (items: FaceGalleryItemDto[], index: number) => ({ items, index }),
);

const selectLightboxHasPrevFace = createSelector(
  selectLightboxFaceIndex,
  (index: number) => index > 0,
);

const selectLightboxHasNextFace = createSelector(
  selectLightboxFaceIndex,
  selectFaceItems,
  (index: number, items: FaceGalleryItemDto[]) => index >= 0 && index < items.length - 1,
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
  selectLightboxKind,
  selectLightboxFaceId,
  selectLightboxVersionId,
  selectLightboxAsset,
  selectLightboxHasPrev,
  selectLightboxHasNext,
  selectLightboxNavContext,
  selectLightboxHasPrevFace,
  selectLightboxHasNextFace,
  selectLightboxFaceNavContext,
  selectSelectionMode,
  selectSelectedIds,
  selectAnchorId,
  selectPersonNameMap,
  selectFaceItems,
  selectFaceTotal,
  selectFaceHasMore,
  selectHashMap,
};
