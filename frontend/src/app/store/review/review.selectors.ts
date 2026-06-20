import { reviewFeature } from './review.reducer';

const { selectAll, selectTotal, selectIsLoading, selectError, selectFaceQueue, selectFaceQueueLoading } = reviewFeature;

export const reviewSelectors = {
  selectAll,
  selectTotal,
  selectIsLoading,
  selectError,
  selectFaceQueue,
  selectFaceQueueLoading,
};
