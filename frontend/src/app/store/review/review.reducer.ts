import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { DupePair, FaceReviewItem } from '@photofant/models';
import { reviewActions } from './review.actions';

export interface ReviewState extends EntityState<DupePair> {
  total: number;
  offset: number;
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  faceQueue: FaceReviewItem[];
  faceQueueLoading: boolean;
}

// Normalize pHash (0-64) onto the same 0-1 scale as CLIP cosine-distance so pairs
// found by either method sort together, best (lowest distance) first.
function bestDistance(pair: DupePair): number {
  const candidates: number[] = [];
  if (pair.phash_distance !== null) candidates.push(pair.phash_distance / 64);
  if (pair.clip_distance !== null) candidates.push(pair.clip_distance);
  return candidates.length > 0 ? Math.min(...candidates) : 1;
}

const adapter: EntityAdapter<DupePair> = createEntityAdapter<DupePair>({
  selectId: (pair: DupePair) => pair.id,
  sortComparer: (a: DupePair, b: DupePair) => bestDistance(a) - bestDistance(b),
});

const initialState: ReviewState = adapter.getInitialState({
  total: 0,
  offset: 0,
  isLoading: false,
  isLoadingMore: false,
  error: null,
  faceQueue: [],
  faceQueueLoading: false,
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
    on(reviewActions.loadDupePairsSuccess, (state: ReviewState, { pairs, total }) =>
      adapter.setAll(pairs, { ...state, total, offset: pairs.length, isLoading: false, error: null }),
    ),
    on(reviewActions.loadDupePairsFailure, (state: ReviewState, { error }) => ({
      ...state,
      isLoading: false,
      error,
    })),
    on(reviewActions.loadMoreDupePairs, (state: ReviewState) => ({
      ...state,
      isLoadingMore: true,
      error: null,
    })),
    on(reviewActions.loadMoreDupePairsSuccess, (state: ReviewState, { pairs, total }) =>
      adapter.addMany(pairs, { ...state, total, offset: state.offset + pairs.length, isLoadingMore: false, error: null }),
    ),
    on(reviewActions.loadMoreDupePairsFailure, (state: ReviewState, { error }) => ({
      ...state,
      isLoadingMore: false,
      error,
    })),
    on(reviewActions.resolveDupePairSuccess, (state: ReviewState, { itemId }) =>
      adapter.removeOne(itemId, { ...state, total: Math.max(0, state.total - 1) }),
    ),
    on(reviewActions.resolveDupePairFailure, (state: ReviewState, { error }) => ({
      ...state,
      error,
    })),
    on(reviewActions.triggerDupeScanFailure, (state: ReviewState, { error }) => ({
      ...state,
      error,
    })),
    on(reviewActions.loadFaceQueue, (state: ReviewState) => ({
      ...state,
      faceQueueLoading: true,
      error: null,
    })),
    on(reviewActions.loadFaceQueueSuccess, (state: ReviewState, { items }) => ({
      ...state,
      faceQueue: items,
      faceQueueLoading: false,
      error: null,
    })),
    on(reviewActions.loadFaceQueueFailure, (state: ReviewState, { error }) => ({
      ...state,
      faceQueueLoading: false,
      error,
    })),
    on(reviewActions.resolveFaceReviewSuccess, (state: ReviewState, { faceId }) => ({
      ...state,
      faceQueue: state.faceQueue.filter((item: FaceReviewItem) => item.face_id !== faceId),
    })),
    on(reviewActions.resolveFaceReviewFailure, (state: ReviewState, { error }) => ({
      ...state,
      error,
    })),
  ),
  extraSelectors: ({ selectReviewState }) => ({
    ...adapter.getSelectors(selectReviewState),
  }),
});
