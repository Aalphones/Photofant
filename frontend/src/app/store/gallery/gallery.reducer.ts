import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { AssetDto } from '@photofant/models';
import { galleryActions } from './gallery.actions';

const PAGE_SIZE = 50;

export interface GalleryState extends EntityState<AssetDto> {
  total: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  error: string | null;
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
      adapter.removeAll({ ...state, page: 1, total: 0, isLoading: true, error: null })
    ),
    on(galleryActions.loadPageSuccess, (state: GalleryState, { items, total, page, pageSize }) =>
      adapter.addMany(items, { ...state, total, page, pageSize, isLoading: false, error: null })
    ),
    on(galleryActions.loadPageFailure, (state: GalleryState, { error }) => ({
      ...state,
      isLoading: false,
      error,
    })),
  ),
  extraSelectors: ({ selectGalleryState }) => ({
    ...adapter.getSelectors(selectGalleryState),
  }),
});
