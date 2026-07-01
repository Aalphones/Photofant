import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { AssetDto, Facets, FaceGalleryItemDto } from '@photofant/models';
import { galleryActions } from './gallery.actions';

const PAGE_SIZE = 100;

export interface GalleryState extends EntityState<AssetDto> {
  total: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  error: string | null;
  lightboxId: number | null;
  lightboxKind: 'asset' | 'face';
  lightboxFaceId: number | null;
  // P21-Stapel: initiale Stage-Auswahl beim Öffnen (welche Version zuerst gezeigt wird)
  lightboxVersionId: number | null;
  lightboxPendingNext: boolean;
  lightboxContextIds: number[] | null;
  facets: Facets | null;
  selectionMode: boolean;
  selectedIds: number[];
  anchorId: number | null;
  faceItems: FaceGalleryItemDto[];
  faceTotal: number;
}

// P21: Version-Pseudo-Einträge teilen ihre `asset.id` mit dem Original — als Entity-Key
// braucht es darum den `version_id` statt `id` für kind === 'version', sonst würde das
// Original oder eine seiner Versionen die andere in der EntityAdapter-Map überschreiben.
const adapter: EntityAdapter<AssetDto> = createEntityAdapter<AssetDto>({
  selectId: (asset: AssetDto) => asset.kind === 'version' ? `v${asset.version_id}` : String(asset.id),
});

const initialState: GalleryState = adapter.getInitialState({
  total: 0,
  page: 1,
  pageSize: PAGE_SIZE,
  isLoading: false,
  error: null,
  lightboxId: null,
  lightboxKind: 'asset',
  lightboxFaceId: null,
  lightboxVersionId: null,
  lightboxPendingNext: false,
  lightboxContextIds: null,
  facets: null,
  selectionMode: false,
  selectedIds: [],
  anchorId: null,
  faceItems: [],
  faceTotal: 0,
});

export const galleryFeature = createFeature({
  name: 'gallery',
  reducer: createReducer(
    initialState,
    on(galleryActions.setPageSize, (state: GalleryState, { pageSize }) => ({
      ...state,
      pageSize,
    })),
    on(galleryActions.requestPage, (state: GalleryState) => ({
      ...state,
      isLoading: true,
      error: null,
    })),
    on(galleryActions.requestNextPage, (state: GalleryState) => ({
      ...state,
      page: state.page + 1,
      isLoading: true,
      error: null,
    })),
    on(galleryActions.reset, (state: GalleryState) =>
      adapter.removeAll({ ...state, page: 1, total: 0, isLoading: true, error: null, facets: null, faceItems: [], faceTotal: 0, lightboxContextIds: null })
    ),
    on(galleryActions.loadFacesPageSuccess, (state: GalleryState, { items, total, page }) => ({
      ...state,
      faceItems: page === 1 ? items : [...state.faceItems, ...items],
      faceTotal: total,
      page,
      // pageSize deliberately NOT updated here — face page size must not overwrite asset page size
      isLoading: false,
      error: null,
    })),
    on(galleryActions.loadPageSuccess, (state: GalleryState, { items, total, page, pageSize, facets }) => {
      const next = adapter.addMany(items, { ...state, total, page, pageSize, isLoading: false, error: null, lightboxPendingNext: false, facets });
      if (state.lightboxPendingNext && items.length > 0) {
        return { ...next, lightboxId: items[0]!.id }; // items.length > 0 guarantees slot exists
      }
      return next;
    }),
    on(galleryActions.loadPageFailure, (state: GalleryState, { error }) => ({
      ...state,
      isLoading: false,
      error,
    })),
    on(galleryActions.injectAsset, (state: GalleryState, { asset }) =>
      adapter.upsertOne(asset, state)
    ),
    on(galleryActions.openLightbox, (state: GalleryState, { id, versionId }) => ({
      ...state, lightboxId: id, lightboxKind: 'asset' as const, lightboxFaceId: null,
      lightboxVersionId: versionId ?? null,
    })),
    on(galleryActions.openFaceLightbox, (state: GalleryState, { faceId, versionId }) => ({
      ...state, lightboxId: null, lightboxKind: 'face' as const, lightboxFaceId: faceId,
      lightboxVersionId: versionId ?? null,
    })),
    on(galleryActions.closeLightbox, (state: GalleryState) => ({
      ...state, lightboxId: null, lightboxKind: 'asset' as const, lightboxFaceId: null,
      lightboxVersionId: null, lightboxPendingNext: false, lightboxContextIds: null,
    })),
    on(galleryActions.setLightboxContext, (state: GalleryState, { assets }) =>
      adapter.upsertMany(assets, { ...state, lightboxContextIds: assets.map((asset: AssetDto) => asset.id) })
    ),
    on(galleryActions.lightboxGoTo, (state: GalleryState, { id }) => ({
      ...state, lightboxId: id, lightboxKind: 'asset' as const, lightboxFaceId: null, lightboxVersionId: null,
    })),
    on(galleryActions.lightboxMarkPendingNext, (state: GalleryState) => ({ ...state, lightboxPendingNext: true })),
    on(galleryActions.toggleFavourite, (state: GalleryState, { id, value }) =>
      adapter.updateOne({ id: String(id), changes: { favourite: value } }, state)
    ),
    on(galleryActions.toggleFavouriteSuccess, (state: GalleryState, { asset }) =>
      adapter.updateOne({ id: String(asset.id), changes: asset }, state)
    ),
    on(galleryActions.toggleFavouriteFailure, (state: GalleryState, { id, previous }) =>
      adapter.updateOne({ id: String(id), changes: { favourite: previous } }, state)
    ),
    on(galleryActions.deleteAssetSuccess, (state: GalleryState, { id }) => {
      const removed = adapter.removeOne(String(id), state);
      return state.lightboxId === id ? { ...removed, lightboxId: null } : removed;
    }),
    // Selection
    on(galleryActions.enableSelectionMode, (state: GalleryState) => ({
      ...state, selectionMode: true, anchorId: null,
    })),
    on(galleryActions.disableSelectionMode, (state: GalleryState) => ({
      ...state, selectionMode: false, selectedIds: [], anchorId: null,
    })),
    on(galleryActions.toggleSelected, (state: GalleryState, { id }) => {
      const isSelected = state.selectedIds.includes(id);
      const selectedIds = isSelected
        ? state.selectedIds.filter((existingId: number) => existingId !== id)
        : [...state.selectedIds, id];
      return { ...state, selectedIds, anchorId: id };
    }),
    on(galleryActions.selectAll, (state: GalleryState, { ids }) => {
      const merged = Array.from(new Set([...state.selectedIds, ...ids]));
      return { ...state, selectedIds: merged };
    }),
    on(galleryActions.selectRange, (state: GalleryState, { ids }) => ({
      ...state, selectedIds: ids,
    })),
    on(galleryActions.clearSelection, (state: GalleryState) => ({
      ...state, selectedIds: [], selectionMode: false, anchorId: null,
    })),
    on(galleryActions.removeFaceItem, (state: GalleryState, { id }) => ({
      ...state,
      faceItems: state.faceItems.filter((item: FaceGalleryItemDto) => item.id !== id),
      faceTotal: Math.max(0, state.faceTotal - 1),
    })),
  ),
  extraSelectors: ({ selectGalleryState }) => ({
    ...adapter.getSelectors(selectGalleryState),
  }),
});
