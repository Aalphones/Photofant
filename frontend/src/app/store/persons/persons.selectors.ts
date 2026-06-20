import { personsFeature } from './persons.reducer';

const {
  selectAll,
  selectIsLoading,
  selectError,
} = personsFeature;

export const personsSelectors = {
  selectAll,
  selectIsLoading,
  selectError,
};
