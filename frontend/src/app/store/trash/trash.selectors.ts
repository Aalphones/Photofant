import { trashFeature } from './trash.reducer';

const { selectAll, selectTotal, selectIsLoading, selectError } = trashFeature;

export const trashSelectors = {
  selectAll,
  selectTotal,
  selectIsLoading,
  selectError,
};
