import { reviewFeature } from './review.reducer';

const { selectAll, selectTotal, selectIsLoading, selectError } = reviewFeature;

export const reviewSelectors = {
  selectAll,
  selectTotal,
  selectIsLoading,
  selectError,
};
