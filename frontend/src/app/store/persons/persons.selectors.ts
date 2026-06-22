import { personsFeature } from './persons.reducer';

const {
  selectAll,
  selectIsLoading,
  selectIsClustering,
  selectError,
} = personsFeature;

export const personsSelectors = {
  selectAll,
  selectIsLoading,
  selectIsClustering,
  selectError,
};
