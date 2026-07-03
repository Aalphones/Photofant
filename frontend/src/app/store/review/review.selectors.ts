import { createSelector } from '@ngrx/store';
import { reviewFeature } from './review.reducer';

const { selectAll, selectTotal, selectIsLoading, selectIsLoadingMore, selectError, selectFaceQueue, selectFaceQueueLoading } = reviewFeature;

// Adapter's `selectTotal` is shadowed onto the loaded-entity count (same pattern as
// gallerySelectors) — read the server-side total straight from feature state for
// "are there more pages" logic.
const selectServerTotal = createSelector(
  reviewFeature.selectReviewState,
  (state) => state.total,
);

const selectOffset = createSelector(
  reviewFeature.selectReviewState,
  (state) => state.offset,
);

const selectHasMore = createSelector(
  selectServerTotal, selectTotal,
  (total: number, loaded: number) => total > loaded,
);

export const reviewSelectors = {
  selectAll,
  selectTotal,
  selectServerTotal,
  selectOffset,
  selectHasMore,
  selectIsLoading,
  selectIsLoadingMore,
  selectError,
  selectFaceQueue,
  selectFaceQueueLoading,
};
