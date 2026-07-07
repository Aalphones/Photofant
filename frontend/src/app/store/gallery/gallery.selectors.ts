import { createSelector } from '@ngrx/store';
import type { AssetDto, FaceGalleryItemDto } from '@photofant/models';
import { filtersFeature } from '../filters/filters.reducer';
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

const selectFetchParams = createSelector(
  selectPage, selectPageSize,
  filtersFeature.selectSort, filtersFeature.selectOrder, filtersFeature.selectFavourite,
  filtersFeature.selectSources, filtersFeature.selectQualityMin, filtersFeature.selectTagIds,
  filtersFeature.selectCollectionId, filtersFeature.selectPersonId, filtersFeature.selectFramings,
  filtersFeature.selectHasFaces, filtersFeature.selectMediaType, filtersFeature.selectClassificationLabelIds,
  filtersFeature.selectReverseSearch, searchFeature.selectQ, searchFeature.selectMode,
  (page, pageSize, sort, order, favourite, sources, qualityMin, tagIds, collectionId, personId, framings, hasFaces, mediaType, classificationLabelIds, reverseSearch, q, qMode) =>
    ({ page, pageSize, sort, order, favourite, sources, qualityMin, tagIds, collectionId, personId, framings, hasFaces, mediaType, classificationLabelIds, similarIds: reverseSearch?.similarIds ?? null, q, qMode })
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
  selectFaceItems,
  selectFaceTotal,
  selectFaceHasMore,
  selectHashMap,
};
