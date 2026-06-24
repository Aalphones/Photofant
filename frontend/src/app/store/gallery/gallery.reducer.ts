import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { AssetDto, Facets, FaceGalleryItemDto } from '@photofant/models';
import { galleryActions } from './gallery.actions';

const PAGE_SIZE = 50;

export interface GalleryState extends EntityState<AssetDto> {
  total: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  error: string | null;
  lightboxId: number | null;
  lightboxPendingNext: boolean;
  lightboxContextIds: number[] | null;
  facets: Facets | null;
  selectionMode: boolean;
  selectedIds: number[];
  faceItems: FaceGalleryItemDto[];
  faceTotal: number;
}

const adapter: EntityAdapter<AssetDto> = createEntityAdapter<AssetDto>({
  selectId: (asset: AssetDto) => asset.id,
});

const initialState: GalleryState = adapter.getInitialState({
  total: 0,
  page: 1,
  pageSize: PAGE_SIZE,
  isLoading: false,
  error: null,
  lightboxId: null,
  lightboxPendingNext: false,
  lightboxContextIds: null,
  facets: null,
  selectionMode: false,
  selectedIds: [],
  faceItems: [],
  faceTotal: 0,
});

export const galleryFeature = createFeature({
  name: 'gallery',
  reducer: createReducer(
    initialState,
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
    on(galleryActions.openLightbox, (state: GalleryState, { id }) => ({ ...state, lightboxId: id })),
    on(galleryActions.closeLightbox, (state: GalleryState) => ({ ...state, lightboxId: null, lightboxPendingNext: false, lightboxContextIds: null })),
    on(galleryActions.setLightboxContext, (state: GalleryState, { assets }) =>
      adapter.upsertMany(assets, { ...state, lightboxContextIds: assets.map((asset: AssetDto) => asset.id) })
    ),
    on(galleryActions.lightboxGoTo, (state: GalleryState, { id }) => ({ ...state, lightboxId: id })),
    on(galleryActions.lightboxMarkPendingNext, (state: GalleryState) => ({ ...state, lightboxPendingNext: true })),
    on(galleryActions.toggleFavourite, (state: GalleryState, { id, value }) =>
      adapter.updateOne({ id, changes: { favourite: value } }, state)
    ),
    on(galleryActions.toggleFavouriteSuccess, (state: GalleryState, { asset }) =>
      adapter.updateOne({ id: asset.id, changes: asset }, state)
    ),
    on(galleryActions.toggleFavouriteFailure, (state: GalleryState, { id, previous }) =>
      adapter.updateOne({ id, changes: { favourite: previous } }, state)
    ),
    on(galleryActions.deleteAssetSuccess, (state: GalleryState, { id }) => {
      const removed = adapter.removeOne(id, state);
      return state.lightboxId === id ? { ...removed, lightboxId: null } : removed;
    }),
    // Selection
    on(galleryActions.enableSelectionMode, (state: GalleryState) => ({
      ...state, selectionMode: true,
    })),
    on(galleryActions.disableSelectionMode, (state: GalleryState) => ({
      ...state, selectionMode: false, selectedIds: [],
    })),
    on(galleryActions.toggleSelected, (state: GalleryState, { id }) => {
      const isSelected = state.selectedIds.includes(id);
      const selectedIds = isSelected
        ? state.selectedIds.filter((existingId: number) => existingId !== id)
        : [...state.selectedIds, id];
      return { ...state, selectedIds };
    }),
    on(galleryActions.selectAll, (state: GalleryState, { ids }) => {
      const merged = Array.from(new Set([...state.selectedIds, ...ids]));
      return { ...state, selectedIds: merged };
    }),
    on(galleryActions.clearSelection, (state: GalleryState) => ({
      ...state, selectedIds: [], selectionMode: false,
    })),
  ),
  extraSelectors: ({ selectGalleryState }) => ({
    ...adapter.getSelectors(selectGalleryState),
  }),
});
