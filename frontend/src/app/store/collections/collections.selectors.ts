import { createSelector } from '@ngrx/store';
import type { Collection } from '@photofant/models';
import { collectionsFeature } from './collections.reducer';

const { selectAll, selectEntities, selectIsLoading, selectError, selectDetail } = collectionsFeature;

const selectSmartAlbums = createSelector(
  selectAll,
  (items: Collection[]) => items.filter((item: Collection) => item.kind === 'smart_album'),
);

// Nur handgeführte Alben — Bulk-Bar "Zu Album" soll weder Smart-Alben (P10, latenter
// Bug: selectAll war vorher unfiltered) noch Trainingssets (eigene Menü-Sektion) zeigen.
const selectAlbums = createSelector(
  selectAll,
  (items: Collection[]) => items.filter((item: Collection) => item.kind === 'album'),
);

const selectTrainingSets = createSelector(
  selectAll,
  (items: Collection[]) => items.filter((item: Collection) => item.kind === 'training_set'),
);

// Alben-Übersicht (album + smart_album) — Trainingssets haben eine eigene Seite und
// sollen dort nicht doppelt auftauchen.
const selectAlbumsAndSmart = createSelector(
  selectAll,
  (items: Collection[]) => items.filter((item: Collection) => item.kind !== 'training_set'),
);

export const collectionsSelectors = {
  selectAll,
  selectEntities,
  selectIsLoading,
  selectError,
  selectDetail,
  selectSmartAlbums,
  selectAlbums,
  selectTrainingSets,
  selectAlbumsAndSmart,
};
