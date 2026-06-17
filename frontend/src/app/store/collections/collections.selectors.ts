import { createSelector } from '@ngrx/store';
import type { Collection } from '@photofant/models';
import { collectionsFeature } from './collections.reducer';

const { selectAll, selectEntities, selectIsLoading, selectError, selectDetail } = collectionsFeature;

const selectSmartAlbums = createSelector(
  selectAll,
  (items: Collection[]) => items.filter((item: Collection) => item.kind === 'smart_album'),
);

export const collectionsSelectors = {
  selectAll,
  selectEntities,
  selectIsLoading,
  selectError,
  selectDetail,
  selectSmartAlbums,
};
