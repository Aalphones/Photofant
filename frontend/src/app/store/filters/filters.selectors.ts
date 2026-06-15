import { filtersFeature } from './filters.reducer';

const {
  selectSort,
  selectOrder,
  selectGroup,
  selectDensity,
  selectFavourite,
} = filtersFeature;

export const filtersSelectors = {
  sort:      selectSort,
  order:     selectOrder,
  group:     selectGroup,
  density:   selectDensity,
  favourite: selectFavourite,
};
