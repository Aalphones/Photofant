import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { DupePair } from '@photofant/models';
import { reviewActions } from './review.actions';

export interface ReviewState extends EntityState<DupePair> {
  isLoading: boolean;
  error: string | null;
}

const adapter: EntityAdapter<DupePair> = createEntityAdapter<DupePair>({
  selectId: (pair: DupePair) => pair.id,
  sortComparer: (a: DupePair, b: DupePair) => a.phash_distance - b.phash_distance,
});

const initialState: ReviewState = adapter.getInitialState({
  isLoading: false,
  error: null,
});

export const reviewFeature = createFeature({
  name: 'review',
  reducer: createReducer(
    initialState,
    on(reviewActions.loadDupePairs, (state: ReviewState) => ({
      ...state,
      isLoading: true,
      error: null,
    })),
    on(reviewActions.loadDupePairsSuccess, (state: ReviewState, { pairs }) =>
      adapter.setAll(pairs, { ...state, isLoading: false, error: null }),
    ),
    on(reviewActions.loadDupePairsFailure, (state: ReviewState, { error }) => ({
      ...state,
      isLoading: false,
      error,
    })),
    on(reviewActions.resolveDupePairSuccess, (state: ReviewState, { itemId }) =>
      adapter.removeOne(itemId, state),
    ),
    on(reviewActions.resolveDupePairFailure, (state: ReviewState, { error }) => ({
      ...state,
      error,
    })),
    on(reviewActions.triggerDupeScanFailure, (state: ReviewState, { error }) => ({
      ...state,
      error,
    })),
  ),
  extraSelectors: ({ selectReviewState }) => ({
    ...adapter.getSelectors(selectReviewState),
  }),
});
