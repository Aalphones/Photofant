import { classificationFeature } from './classification.reducer';

const { selectAll, selectEntities, selectTotal, selectIsLoading, selectError } = classificationFeature;

export const classificationSelectors = {
  selectAll,
  selectEntities,
  selectTotal,
  selectIsLoading,
  selectError,
};
