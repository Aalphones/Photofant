import { tagsFeature } from './tags.reducer';

const { selectAll, selectTotal, selectIsLoading, selectError } = tagsFeature;

export const tagsSelectors = {
  selectAll,
  selectTotal,
  selectIsLoading,
  selectError,
};
